import copy
import unittest
from configparser import ConfigParser
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import ValidationError

from ..utils.config import ShopifyConfig


class TestShopifyConfig(unittest.TestCase):
    valid_config = {
        "api_token": "shpat_1234567890abcdef",
        "shop_url_key": "my-shop",
        "api_key": "0123456789abcdef0123456789abcdef",
        "api_secret": "fedcba9876543210fedcba9876543210",
    }
    config_path = Path(__file__).parent.parent.parent.parent.parent.parent / "odoo17.local.cfg"
    good_config = ConfigParser()
    good_config.read(config_path)

    def test_valid_config(self) -> None:
        config = ShopifyConfig(**self.valid_config)

        for key, value in self.valid_config.items():
            self.assertEqual(getattr(config, key), value)

    def test_invalid_configs(self) -> None:
        invalid_configs = [
            {"api_token": "invalid"},
            {"shop_url_key": "invalid.com"},
            {"api_key": "invalid"},
            {"api_secret": "invalid"},
        ]

        for invalid_field in invalid_configs:
            with self.subTest(invalid_field=list(invalid_field.keys())[0]):
                test_config = self.valid_config.copy()
                test_config.update(invalid_field)
                with self.assertRaises(ValidationError):
                    ShopifyConfig(**test_config)

    def test_from_odoo_config(self) -> None:
        config = ShopifyConfig.from_odoo_config(self.config_path)
        self.assertIsInstance(config, ShopifyConfig)
        self.assertTrue(config.api_token.startswith("shpat_"))
        self.assertTrue(config.shop_url_key.isalnum() or "-" in config.shop_url_key)
        self.assertEqual(len(config.api_key), 32)
        self.assertEqual(len(config.api_secret), 32)

    def test_from_odoo_config_missing_file(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ShopifyConfig.from_odoo_config(Path("missing_file.cfg"))

    def test_from_odoo_config_missing_section(self) -> None:
        missing_section_config = copy.deepcopy(self.good_config)
        missing_section_config.remove_section("shopify")
        with NamedTemporaryFile() as bad_config_path:
            with open(bad_config_path.name, "w") as bad_config_file:
                missing_section_config.write(bad_config_file)
            with self.assertRaises(ValueError):
                ShopifyConfig.from_odoo_config(Path(bad_config_path.name))

    def test_from_odoo_config_missing_key(self) -> None:
        missing_key_config = copy.deepcopy(self.good_config)
        missing_key_config.remove_option("shopify", "api_token")
        with NamedTemporaryFile() as bad_config_path:
            with open(bad_config_path.name, "w") as bad_config_file:
                missing_key_config.write(bad_config_file)
            with self.assertRaises(ValidationError):
                ShopifyConfig.from_odoo_config(Path(bad_config_path.name))


if __name__ == "__main__":
    unittest.main()
