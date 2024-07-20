import logging
import re
from configparser import ConfigParser
from pathlib import Path

from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)


# noinspection PyMethodParameters
class ShopifyConfig(BaseModel):
    api_token: str
    shop_url_key: str
    api_key: str
    api_secret: str

    @field_validator("api_token")
    def validate_api_token(cls, v: str) -> str:
        if not v.startswith("shpat_"):
            raise ValueError("Invalid API token format. Must start with 'shpat_'")
        return v

    @field_validator("shop_url_key")
    def validate_shop_url_key(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9-]+$", v):
            raise ValueError("Invalid shop URL name.")
        return v

    @field_validator("api_key", "api_secret")
    def validate_key_secret(cls, v: str) -> str:
        if len(v) != 32:
            raise ValueError("Invalid Shopify API key or secret format")
        return v

    @classmethod
    def from_odoo_config(cls, config_path: Path) -> "ShopifyConfig":
        logger.debug(f"Loading Shopify configuration from {config_path}")
        if not config_path.exists():
            message = f"Configuration file not found: {config_path}"
            logger.error(message)
            raise FileNotFoundError(message)
        config = ConfigParser()
        config.read(config_path)

        if "shopify" in config.sections():
            shopify_config = {key: value for key, value in config.items("shopify")}
            return cls(**shopify_config)

        message = "No 'shopify' section found in configuration file."
        logger.error(message)
        raise ValueError(message)
