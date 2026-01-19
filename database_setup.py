import os
import sys
import psycopg2
import psycopg2.pool
import logging
import time
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# 載入環境變數
load_dotenv('config.env')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    # 類別變數 - 全域連線池
    _pool = None
    
    def __init__(self):
        """初始化數據庫管理器"""
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'stockhunter'),
            'password': os.getenv('DB_PASSWORD', 'stockhunter123'),
            'database': os.getenv('DB_NAME', 'stockhunter')
        }
        
        # 如果連線池不存在，則初始化連線池
        if DatabaseManager._pool is None:
            self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化連線池"""
        try:
            logger.info("正在初始化資料庫連線池...")
            DatabaseManager._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database']
            )
            logger.info("✅ 資料庫連線池初始化成功 (最小連線: 1, 最大連線: 10)")
        except Exception as e:
            logger.error(f"❌ 連線池初始化失敗: {e}")
            DatabaseManager._pool = None
            raise e
        
    def create_database(self):
        """創建數據庫"""
        try:
            # 連接到PostgreSQL（不指定數據庫）
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # 檢查數據庫是否存在
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'stockhunter'")
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute("CREATE DATABASE stockhunter")
                logger.info("數據庫 'stockhunter' 創建成功")
            else:
                logger.info("數據庫 'stockhunter' 已存在")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"創建數據庫失敗: {e}")
            return False

    def create_tables(self):
        """創建必要的表 - 按照FinMind API文檔順序，欄位順序與API回傳順序一致"""
        try:
            # 為了避免連線池問題，在這裡直接創建新連線
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database='stockhunter'
            )
            cursor = conn.cursor()
            
            # 1. 台股總覽 (TaiwanStockInfo)
            # API回傳順序: industry_category, stock_id, stock_name, type, date
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_info_data (
                    id SERIAL PRIMARY KEY,
                    industry_category VARCHAR(200),
                    stock_id VARCHAR(20) NOT NULL,
                    stock_name VARCHAR(200),
                    type VARCHAR(50),
                    date VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id)
                )
            """)
            
            # 2. 台股總覽(含權證) (TaiwanStockInfoWithWarrant)
            # API回傳順序: industry_category, stock_id, stock_name, type, date
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_info_with_warrant_data (
                    id SERIAL PRIMARY KEY,
                    industry_category VARCHAR(200),
                    stock_id VARCHAR(20) NOT NULL,
                    stock_name VARCHAR(200),
                    type VARCHAR(50),
                    date VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id)
                )
            """)
            
            # 3. 台股交易日 (TaiwanStockTradingDate)
            # API回傳順序: date
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_trading_date_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. 股價日成交資訊 (TaiwanStockPrice)
            # API回傳順序: date, stock_id, Trading_Volume, Trading_money, open, max, min, close, spread, Trading_turnover
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_price_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    Trading_Volume BIGINT,
                    Trading_money BIGINT,
                    open DECIMAL(10, 2),
                    max DECIMAL(10, 2),
                    min DECIMAL(10, 2),
                    close DECIMAL(10, 2),
                    spread DECIMAL(10, 2),
                    Trading_turnover DECIMAL(10, 4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 5. 個股PER、PBR資料表 (TaiwanStockPER)
            # API回傳順序: date, stock_id, dividend_yield, per, pbr
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_per_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    dividend_yield DECIMAL(10, 4),
                    per DECIMAL(10, 4),
                    pbr DECIMAL(10, 4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 6. 每5秒委託成交統計 (TaiwanStockStatisticsOfOrderBookAndTrade)
            # API回傳順序: time, date, total_buy_order, total_buy_volume, total_sell_order, total_sell_volume, total_deal_order, total_deal_volume, total_deal_money
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_statistics_of_order_book_and_trade_data (
                    id SERIAL PRIMARY KEY,
                    time VARCHAR(20) NOT NULL,
                    date DATE NOT NULL,
                    total_buy_order BIGINT,
                    total_buy_volume BIGINT,
                    total_sell_order BIGINT,
                    total_sell_volume BIGINT,
                    total_deal_order BIGINT,
                    total_deal_volume BIGINT,
                    total_deal_money BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, time)
                )
            """)
            
            # 7. 加權指數 (TaiwanVariousIndicators5Seconds)
            # API回傳順序: date, TAIEX
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS various_indicators5_seconds_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    TAIEX DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            """)
            
            # 8. 當日沖銷交易標的及成交量值 (TaiwanStockDayTrading)
            # API回傳順序: stock_id, date, buy_after_sale, volume, buy_amount, sell_amount
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_day_trading_data (
                    id SERIAL PRIMARY KEY,
                    stock_id VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    buy_after_sale VARCHAR(50),
                    volume BIGINT,
                    buy_amount BIGINT,
                    sell_amount BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 9. 加權、櫃買報酬指數 (TaiwanStockTotalReturnIndex)
            # API回傳順序: date, stock_id, price
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_total_return_index_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(20) NOT NULL,
                    price DECIMAL(10, 4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 10. 個股融資融劵表 (TaiwanStockMarginPurchaseShortSale)
            # API回傳順序: date, stock_id, MarginPurchaseToday, MarginSaleToday, ...
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_margin_purchase_short_sale_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    MarginPurchaseToday BIGINT,
                    MarginSaleToday BIGINT,
                    OffsetTodayMarginPurchase BIGINT,
                    OffsetTodayMarginSale BIGINT,
                    MarginPurchaseYesterday BIGINT,
                    MarginSaleYesterday BIGINT,
                    ShortSaleToday BIGINT,
                    ShortCoveringToday BIGINT,
                    OffsetTodayShortSale BIGINT,
                    OffsetTodayShortCovering BIGINT,
                    ShortSaleYesterday BIGINT,
                    ShortCoveringYesterday BIGINT,
                    Quota BIGINT,
                    Note VARCHAR(200),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 11. 台灣市場整體融資融劵表 (TaiwanStockTotalMarginPurchaseShortSale)
            # API回傳順序: date, name, TodayBalance, YesBalance, buy, Return, sell
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_total_margin_purchase_short_sale_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    name VARCHAR(200),
                    TodayBalance BIGINT,
                    YesBalance BIGINT,
                    buy BIGINT,
                    Return BIGINT,
                    sell BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, name)
                )
            """)
            
            # 12. 法人買賣表 (TaiwanStockInstitutionalInvestorsBuySell)
            # API回傳順序: date, stock_id, buy, name, sell
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_institutional_investors_buy_sell_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    buy BIGINT,
                    name VARCHAR(200),
                    sell BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date, name)
                )
            """)
            
            # 13. 台灣市場整體法人買賣表 (TaiwanStockTotalInstitutionalInvestors)
            # API回傳順序: date, name, buy, sell
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_total_institutional_investors_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    name VARCHAR(200),
                    buy BIGINT,
                    sell BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, name)
                )
            """)
            
            # 14. 外資持股表 (TaiwanStockShareholding)
            # API回傳順序: date, stock_id, stock_name, InternationalCode, ForeignInvestmentRemainingShares, ...
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_shareholding_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    stock_name VARCHAR(200),
                    InternationalCode VARCHAR(50),
                    ForeignInvestmentRemainingShares BIGINT,
                    ForeignInvestmentShares BIGINT,
                    ForeignInvestmentRemainRatio DECIMAL(10, 4),
                    ForeignInvestmentSharesRatio DECIMAL(10, 4),
                    ForeignInvestmentUpperLimitRatio DECIMAL(10, 4),
                    ChineseInvestmentUpperLimitRatio DECIMAL(10, 4),
                    NumberOfSharesIssued BIGINT,
                    RecentlyDeclareDate VARCHAR(20),
                    note VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 15. 借券成交明細 (TaiwanStockSecuritiesLending)
            # API回傳順序: date, stock_id, transaction_type, volume, fee_rate, close, original_return_date, original_lending_period
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_securities_lending_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    transaction_type VARCHAR(50),
                    volume BIGINT,
                    fee_rate DECIMAL(10, 6),
                    close DECIMAL(10, 2),
                    original_return_date DATE,
                    original_lending_period INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date, transaction_type, volume, fee_rate)
                )
            """)
            
            # 16. 暫停融券賣出表(融券回補日) (TaiwanStockMarginShortSaleSuspension)
            # API回傳順序: stock_id, date, end_date, reason
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_margin_short_sale_suspension_data (
                    id SERIAL PRIMARY KEY,
                    stock_id VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    end_date DATE,
                    reason VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 17. 信用額度總量管制餘額表 (TaiwanDailyShortSaleBalances)
            # API回傳順序: stock_id, date, MarginShortSalesPreviousDayBalance, MarginShortSalesShortSales, ...
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_short_sale_balances_data (
                    id SERIAL PRIMARY KEY,
                    stock_id VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    MarginShortSalesPreviousDayBalance BIGINT,
                    MarginShortSalesShortSales BIGINT,
                    MarginShortSalesShortCovering BIGINT,
                    MarginShortSalesStockRedemption BIGINT,
                    MarginShortSalesCurrentDayBalance BIGINT,
                    MarginShortSalesQuota BIGINT,
                    SBLShortSalesPreviousDayBalance BIGINT,
                    SBLShortSalesShortSales BIGINT,
                    SBLShortSalesReturns BIGINT,
                    SBLShortSalesAdjustments BIGINT,
                    SBLShortSalesCurrentDayBalance BIGINT,
                    SBLShortSalesQuota BIGINT,
                    SBLShortSalesShortCovering BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 18. 證券商資訊表 (TaiwanSecuritiesTraderInfo)
            # API回傳順序: securities_trader_id, securities_trader, date, address, phone
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS securities_trader_info_data (
                    id SERIAL PRIMARY KEY,
                    securities_trader_id VARCHAR(20) NOT NULL,
                    securities_trader VARCHAR(200),
                    date VARCHAR(20),
                    address VARCHAR(500),
                    phone VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(securities_trader_id)
                )
            """)
            
            # 19. 綜合損益表 (TaiwanStockFinancialStatements)
            # API回傳順序: date, stock_id, type, value, origin_name
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_financial_statements_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    type VARCHAR(200),
                    value DECIMAL(20, 2),
                    origin_name VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date, type)
                )
            """)

            # 20. 資產負債表 (TaiwanStockBalanceSheet)
            # API回傳順序: date, stock_id, type, value, origin_name
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_balance_sheet_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    type VARCHAR(200),
                    value DECIMAL(20, 2),
                    origin_name VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date, type)
                )
            """)

            # 21. 現金流量表 (TaiwanStockCashFlowsStatement)
            # API回傳順序: date, stock_id, type, value, origin_name
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_cash_flows_statement_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    type VARCHAR(200),
                    value DECIMAL(20, 2),
                    origin_name VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date, type)
                )
            """)
            
            # 22. 股利政策表 (TaiwanStockDividend)
            # API回傳順序: date, stock_id, year, StockEarningsDistribution, ...
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_dividend_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    year VARCHAR(10),
                    StockEarningsDistribution DECIMAL(20, 2),
                    StockStatutorySurplus DECIMAL(20, 2),
                    StockExDividendTradingDate VARCHAR(20),
                    TotalEmployeeStockDividend DECIMAL(20, 2),
                    TotalEmployeeStockDividendAmount DECIMAL(20, 2),
                    RatioOfEmployeeStockDividendOfTotal DECIMAL(10, 4),
                    RatioOfEmployeeStockDividend DECIMAL(10, 4),
                    CashEarningsDistribution DECIMAL(20, 2),
                    CashStatutorySurplus DECIMAL(20, 2),
                    CashExDividendTradingDate VARCHAR(20),
                    CashDividendPaymentDate VARCHAR(20),
                    TotalEmployeeCashDividend DECIMAL(20, 2),
                    TotalNumberOfCashCapitalIncrease DECIMAL(20, 2),
                    CashIncreaseSubscriptionRate DECIMAL(10, 4),
                    CashIncreaseSubscriptionpRrice DECIMAL(10, 2),
                    RemunerationOfDirectorsAndSupervisors DECIMAL(20, 2),
                    ParticipateDistributionOfTotalShares DECIMAL(20, 2),
                    AnnouncementDate VARCHAR(20),
                    AnnouncementTime VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date, year)
                )
            """)
            
            # 23. 除權除息結果表 (TaiwanStockDividendResult)
            # API回傳順序: date, stock_id, before_price, after_price, ...
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_dividend_result_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    before_price DECIMAL(10, 2),
                    after_price DECIMAL(10, 2),
                    stock_and_cache_dividend DECIMAL(10, 2),
                    stock_or_cache_dividend VARCHAR(20),
                    max_price DECIMAL(10, 2),
                    min_price DECIMAL(10, 2),
                    open_price DECIMAL(10, 2),
                    reference_price DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 24. 月營收表 (TaiwanStockMonthRevenue)
            # API回傳順序: date, stock_id, country, revenue, revenue_month, revenue_year
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_month_revenue_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    country VARCHAR(50),
                    revenue BIGINT,
                    revenue_month INTEGER,
                    revenue_year INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 25. 減資恢復買賣參考價格 (TaiwanStockCapitalReductionReferencePrice)
            # API回傳順序: date, stock_id, ClosingPriceonTheLastTradingDay, PostReductionReferencePrice, LimitUp, LimitDown, OpeningReferencePrice, ExrightReferencePrice, ReasonforCapitalReduction
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_capital_reduction_reference_price_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    ClosingPriceonTheLastTradingDay DECIMAL(10, 2),
                    PostReductionReferencePrice DECIMAL(10, 2),
                    LimitUp DECIMAL(10, 2),
                    LimitDown DECIMAL(10, 2),
                    OpeningReferencePrice DECIMAL(10, 2),
                    ExrightReferencePrice DECIMAL(10, 2),
                    ReasonforCapitalReduction VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 26. 台灣股票下市櫃表 (TaiwanStockDelisting)
            # API回傳順序: date, stock_id, stock_name
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_delisting_data (
                    id SERIAL PRIMARY KEY,
                    stock_id VARCHAR(10) NOT NULL,
                    stock_name VARCHAR(200),
                    delisting_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id)
                )
            """)
            
            # 27. 台股分割後參考價 (TaiwanStockSplitPrice)
            # API回傳順序: date, stock_id, type, before_price, after_price, max_price, min_price, open_price
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_split_price_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    type VARCHAR(50),
                    before_price DECIMAL(10, 2),
                    after_price DECIMAL(10, 2),
                    max_price DECIMAL(10, 2),
                    min_price DECIMAL(10, 2),
                    open_price DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 台灣股票變更面額恢復買賣參考價格 - TaiwanStockParValueChange
            # API回傳順序: date, stock_id, stock_name, before_close, after_ref_close, after_ref_max, after_ref_min, after_ref_open
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_par_value_change_data (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    stock_id VARCHAR(10) NOT NULL,
                    stock_name VARCHAR(100),
                    before_close DECIMAL(10, 2),
                    after_ref_close DECIMAL(10, 2),
                    after_ref_max DECIMAL(10, 2),
                    after_ref_min DECIMAL(10, 2),
                    after_ref_open DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_id, date)
                )
            """)
            
            # 創建索引以提高查詢性能 - 按照表格順序創建
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_info_data_stock_id ON stock_info_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_info_with_warrant_data_stock_id ON stock_info_with_warrant_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_trading_date_data_date ON stock_trading_date_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_price_data_stock_id ON stock_price_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_price_data_date ON stock_price_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_price_data_stock_id_date ON stock_price_data(stock_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_per_data_stock_id ON stock_per_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_per_data_date ON stock_per_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_statistics_order_book_trade_data_date ON stock_statistics_of_order_book_and_trade_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_various_indicators5_seconds_data_date ON various_indicators5_seconds_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_day_trading_data_stock_id ON stock_day_trading_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_day_trading_data_date ON stock_day_trading_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_total_return_index_data_stock_id ON stock_total_return_index_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_total_return_index_data_date ON stock_total_return_index_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_margin_purchase_short_sale_data_stock_id ON stock_margin_purchase_short_sale_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_margin_purchase_short_sale_data_date ON stock_margin_purchase_short_sale_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_total_margin_purchase_short_sale_data_date ON stock_total_margin_purchase_short_sale_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_institutional_investors_buy_sell_data_stock_id ON stock_institutional_investors_buy_sell_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_institutional_investors_buy_sell_data_date ON stock_institutional_investors_buy_sell_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_total_institutional_investors_data_date ON stock_total_institutional_investors_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_shareholding_data_stock_id ON stock_shareholding_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_shareholding_data_date ON stock_shareholding_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_securities_lending_data_stock_id ON stock_securities_lending_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_securities_lending_data_date ON stock_securities_lending_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_margin_short_sale_suspension_data_stock_id ON stock_margin_short_sale_suspension_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_margin_short_sale_suspension_data_date ON stock_margin_short_sale_suspension_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_short_sale_balances_data_stock_id ON daily_short_sale_balances_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_short_sale_balances_data_date ON daily_short_sale_balances_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_securities_trader_info_data_trader_id ON securities_trader_info_data(securities_trader_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_financial_statements_data_stock_id ON stock_financial_statements_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_financial_statements_data_date ON stock_financial_statements_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_balance_sheet_data_stock_id ON stock_balance_sheet_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_balance_sheet_data_date ON stock_balance_sheet_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_cash_flows_statement_data_stock_id ON stock_cash_flows_statement_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_cash_flows_statement_data_date ON stock_cash_flows_statement_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_dividend_data_stock_id ON stock_dividend_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_dividend_data_date ON stock_dividend_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_dividend_result_data_stock_id ON stock_dividend_result_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_dividend_result_data_date ON stock_dividend_result_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_month_revenue_data_stock_id ON stock_month_revenue_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_month_revenue_data_date ON stock_month_revenue_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_capital_reduction_data_stock_id ON stock_capital_reduction_reference_price_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_capital_reduction_data_date ON stock_capital_reduction_reference_price_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_delisting_data_stock_id ON stock_delisting_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_split_price_data_stock_id ON stock_split_price_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_split_price_data_date ON stock_split_price_data(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_par_value_change_data_stock_id ON stock_par_value_change_data(stock_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_par_value_change_data_date ON stock_par_value_change_data(date)")
            
            conn.commit()
            print("✅ 所有表格已成功創建並已按照FinMind API文檔順序重新整理")
            print("📊 共創建了28個表格及相應的索引")
            cursor.close()
            conn.close()  # 在 create_tables 中直接關閉連線，而不是歸還到連線池
            return True
            
        except Exception as e:
            print(f"❌ 創建表格時發生錯誤: {e}")
            if 'conn' in locals() and conn:
                conn.close()  # 在出錯時直接關閉連線
            return False
            
    def drop_all_tables(self):
        """刪除所有表格 - 按照表格順序刪除"""
        try:
            # 為了避免連線池問題，在這裡直接創建新連線
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database='stockhunter'
            )
            cursor = conn.cursor()
            
            # 按照相反順序刪除表格（避免外鍵約束問題）
            tables = [
                'stock_par_value_change_data',
                'stock_split_price_data',
                'stock_delisting_data', 
                'stock_capital_reduction_reference_price_data',
                'stock_month_revenue_data',
                'stock_dividend_result_data',
                'stock_dividend_data',
                'stock_cash_flows_statement_data',
                'stock_balance_sheet_data',
                'stock_financial_statements_data',
                'securities_trader_info_data',
                'daily_short_sale_balances_data',
                'stock_margin_short_sale_suspension_data',
                'stock_securities_lending_data',
                'stock_shareholding_data',
                'stock_total_institutional_investors_data',
                'stock_institutional_investors_buy_sell_data',
                'stock_total_margin_purchase_short_sale_data',
                'stock_margin_purchase_short_sale_data',
                'stock_total_return_index_data',
                'stock_day_trading_data',
                'various_indicators5_seconds_data',
                'stock_statistics_of_order_book_and_trade_data',
                'stock_per_data',
                'stock_price_data',
                'stock_trading_date_data',
                'stock_info_with_warrant_data',
                'stock_info_data'
            ]
            
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"✅ 表格 {table} 已刪除")
            
            conn.commit()
            print("✅ 所有表格已成功刪除")
            cursor.close()
            conn.close()  # 在 drop_all_tables 中直接關閉連線
            
        except Exception as e:
            print(f"❌ 刪除表格時發生錯誤: {e}")
            if 'conn' in locals() and conn:
                conn.close()  # 在出錯時直接關閉連線

    def reset_database(self):
        """重置資料庫 - 刪除所有表格後重新創建"""
        print("🔄 開始重置資料庫...")
        self.drop_all_tables()
        print("⏳ 等待資料庫操作完成...")
        time.sleep(2)
        self.create_tables()
        print("✅ 資料庫重置完成")
    
    def get_connection(self):
        """從連線池獲取數據庫連接"""
        try:
            if DatabaseManager._pool is None:
                logger.error("❌ 連線池未初始化")
                return None
            
            conn = DatabaseManager._pool.getconn()
            logger.debug("✅ 從連線池獲取連線成功")
            return conn
        except Exception as e:
            logger.error(f"❌ 從連線池獲取連線失敗: {e}")
            return None
    
    def return_connection(self, conn):
        """將連線歸還到連線池"""
        try:
            if DatabaseManager._pool is None:
                logger.error("❌ 連線池未初始化，無法歸還連線")
                return False
            
            if conn is not None:
                DatabaseManager._pool.putconn(conn)
                logger.debug("✅ 連線已歸還到連線池")
                return True
            else:
                logger.warning("⚠️ 嘗試歸還空連線")
                return False
        except Exception as e:
            logger.error(f"❌ 歸還連線到連線池失敗: {e}")
            return False

def main():
    """主函數"""
    db_manager = DatabaseManager()
    
    # 檢查數據庫是否已存在，如果存在則直接創建表
    try:
        conn = db_manager.get_connection()
        if conn:
            db_manager.return_connection(conn)
            logger.info("數據庫連接成功，開始創建表...")
            db_manager.create_tables()
            logger.info("數據庫設置完成！")
        else:
            logger.error("無法連接到數據庫！")
    except Exception as e:
        logger.error(f"數據庫設置失敗: {e}")
        # 嘗試創建數據庫
        if db_manager.create_database():
            # 創建表
            db_manager.create_tables()
            logger.info("數據庫設置完成！")
        else:
            logger.error("數據庫設置失敗！")

if __name__ == "__main__":
    main()
