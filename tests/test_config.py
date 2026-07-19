import importlib
import os
import unittest
from unittest.mock import patch

import config


class DataDirectoryConfigurationTests(unittest.TestCase):
    def test_sales_data_dir_keeps_runtime_state_outside_release(self):
        data_dir = os.path.join(os.sep, "var", "lib", "sales-bot")
        environment = patch.dict(os.environ, {"SALES_DATA_DIR": data_dir})

        environment.start()
        try:
            reloaded = importlib.reload(config)
            self.assertEqual(reloaded.DATABASE_PATH, os.path.join(data_dir, "sales.db"))
            self.assertEqual(reloaded.PRODUCTS_FILE, os.path.join(data_dir, "products.json"))
        finally:
            environment.stop()
            importlib.reload(config)


if __name__ == "__main__":
    unittest.main()
