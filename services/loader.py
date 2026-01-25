import pandas as pd
from core.database import DatabaseManager
from core.config import logger

class DataLoader:
    def __init__(self):
        self.db_manager = DatabaseManager()

    def get_merged_data(self, stock_id: str, start_date: str = '2000-01-01', end_date: str = '2100-01-01') -> pd.DataFrame:
        """
        獲取整合後的股票數據 (包含股價、法人買賣、財報等)
        自動處理不同頻率數據的合併 (每日 vs 每月 vs 每季)
        """
        logger.info(f"正在獲取股票 {stock_id} 的整合數據...")
        
        with self.db_manager.get_db_context() as conn:
            if not conn:
                logger.error("無法連接資料庫")
                return pd.DataFrame()

            # 1. 基礎股價 (日頻率) - 主表
            # ------------------------------------------------------------------
            query_price = f"""
                SELECT date, open, max, min, close, Trading_Volume, Trading_money
                FROM stock_price_data
                WHERE stock_id = '{stock_id}' 
                AND date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY date
            """
            df = pd.read_sql(query_price, conn)
            
            if df.empty:
                logger.warning(f"找不到股票 {stock_id} 的股價資料")
                return pd.DataFrame()
                
            # 確保 date 是 datetime 類型，並設為 Index
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 2. 三大法人買賣超 (日頻率)
            # ------------------------------------------------------------------
            # 注意：法人表是 'normalized' 格式 (每天每人一筆)，需要轉置 (Pivot)
            query_inst = f"""
                SELECT date, name, buy, sell
                FROM stock_institutional_investors_buy_sell_data
                WHERE stock_id = '{stock_id}'
                AND date BETWEEN '{start_date}' AND '{end_date}'
            """
            df_inst = pd.read_sql(query_inst, conn)
            if not df_inst.empty:
                df_inst['date'] = pd.to_datetime(df_inst['date'])
                # 計算「買賣超」 = buy - sell
                df_inst['net_buy'] = df_inst['buy'] - df_inst['sell']
                
                # Pivot: Index=date, Column=name, Value=net_buy
                # e.g. Columns: [外資, 投信, 自營商]
                df_inst_pivot = df_inst.pivot_table(
                    index='date', 
                    columns='name', 
                    values='net_buy',
                    aggfunc='sum' # 防呆：萬一同一天同法人有多筆
                )
                # 重新命名欄位，加上前綴以免搞混
                df_inst_pivot.columns = [f"法人_{c}" for c in df_inst_pivot.columns]
                
                # 合併進主表 (Left Join)
                df = df.join(df_inst_pivot, how='left')

            # 3. 本益比/股價淨值比 (日頻率)
            # ------------------------------------------------------------------
            query_per = f"""
                SELECT date, per, pbr, dividend_yield
                FROM stock_per_data
                WHERE stock_id = '{stock_id}'
                AND date BETWEEN '{start_date}' AND '{end_date}'
            """
            df_per = pd.read_sql(query_per, conn)
            if not df_per.empty:
                df_per['date'] = pd.to_datetime(df_per['date'])
                df_per.set_index('date', inplace=True)
                df = df.join(df_per, how='left')

            # 4. 月營收 (月頻率) -> 轉換為日頻率 (Forward Fill)
            # ------------------------------------------------------------------
            query_rev = f"""
                SELECT date, revenue, revenue_month, revenue_year
                FROM stock_month_revenue_data
                WHERE stock_id = '{stock_id}'
                AND date BETWEEN '{start_date}' AND '{end_date}'
            """
            df_rev = pd.read_sql(query_rev, conn)
            if not df_rev.empty:
                df_rev['date'] = pd.to_datetime(df_rev['date'])
                df_rev.set_index('date', inplace=True)
                # 重新命名
                df_rev = df_rev.rename(columns={'revenue': '月營收'})
                
                # 合併後使用 ffill (向前填補)
                # 邏輯：在下個月營收公布前，都假設是這個營收 (或者可以不填補，看分析需求)
                # 這裡示範 Join 後填補
                df = df.join(df_rev[['月營收']], how='left')
                df['月營收'] = df['月營收'].ffill()

            # 5. 綜合損益表 (季頻率) -> EPS
            # ------------------------------------------------------------------
            query_eps = f"""
                SELECT date, value as eps
                FROM stock_financial_statements_data
                WHERE stock_id = '{stock_id}'
                AND type = 'EPS'
                AND date BETWEEN '{start_date}' AND '{end_date}'
            """
            df_eps = pd.read_sql(query_eps, conn)
            if not df_eps.empty:
                df_eps['date'] = pd.to_datetime(df_eps['date'])
                df_eps.set_index('date', inplace=True)
                
                df = df.join(df_eps, how='left')
                df['eps'] = df['eps'].ffill()

            # 填補空值 (法人沒動作可能是 0，但 PER 沒資料就是 NaN)
            # 這邊只對法人欄位補 0
            for col in df.columns:
                if col.startswith('法人_'):
                    df[col] = df[col].fillna(0)

        logger.info(f"整合完成！共 {len(df)} 筆資料，欄位: {list(df.columns)}")
        return df

# 使用範例:
# if __name__ == "__main__":
#     loader = DataLoader()
#     df = loader.get_merged_data("2330", "2023-01-01", "2023-12-31")
#     print(df.tail())
