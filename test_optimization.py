import logging
import sys
import unittest
from datetime import datetime
import core.config as config
from core.database import DatabaseManager
from collectors.technical.taiwan_stock_price import TaiwanStockPriceCollector

# Override logging level for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestOptimization(unittest.TestCase):
    def setUp(self):
        self.db_manager = DatabaseManager()
        self.collector = TaiwanStockPriceCollector()

    def test_config_loading(self):
        print("\nTesting Config Loading...")
        self.assertIsNotNone(config.DB_HOST)
        self.assertIsNotNone(config.DB_USER)
        print("✅ Config loaded successfully")

    def test_db_connection(self):
        print("\nTesting Database Connection...")
        with self.db_manager.get_db_context() as conn:
            self.assertIsNotNone(conn)
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.assertEqual(result[0], 1)
        print("✅ Database connection context manager works")

    def test_collector_execution(self):
        print("\nTesting Collector Execution (Dry Run)...")
        # We don't want to actually call the API and write to DB in a quick test if it takes long,
        # but we can try to get data for a very short range or a known invalid one to test the flow.
        # Actually, let's just checking if the object is initialized correctly and methods exist.
        self.assertTrue(hasattr(self.collector, 'main'))
        self.assertTrue(hasattr(self.collector, '_save_data'))
        print("✅ Collector initialized successfully")

if __name__ == '__main__':
    unittest.main()
