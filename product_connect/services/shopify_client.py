import datetime
import json
import logging
import os
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import odoo
from dotenv import load_dotenv
from odoo import models, api, fields
from sgqlc import introspection
from sgqlc.codegen.schema import CodeGen
from sgqlc.endpoint.http import HTTPEndpoint
from sgqlc.operation import Operation

_logger = logging.getLogger(__name__)


class ShopifyClient(models.TransientModel):
    _name = "shopify.client"
    _description = "Shopify GraphQL API Client"

    store_url_key = fields.Char()
    api_version = fields.Char()
    api_token = fields.Char()
    store_url = fields.Char()
    endpoint_url = fields.Char()

    _session_available_points = 2000
    _session_last_leak_time = int(time.time())
    _session_max_bucket_size = 2000
    _session_leak_rate = 100

    _endpoint: HTTPEndpoint = None
    _schema_module: ModuleType | None = None

    @api.model_create_multi
    def create(self, vals_list: list["odoo.values.shopify_client"]) -> "ShopifyClient":
        if self.env.context.get("use_dotenv"):
            self._overwrite_settings_from_dotenv()
        clients = super().create(vals_list)
        for client in clients:
            client._settings_from_db()
            client._check_and_generate_schema_models()
        return clients

    def _check_and_generate_schema_models(self, retries: int = 3) -> None:
        schema_path = self._get_current_schema_path()
        models_path = self._get_current_models_path()

        for folder in [schema_path.parent, models_path.parent]:
            if not folder.exists():
                folder.mkdir()

        (models_path.parent / "__init__.py").touch()

        has_new_schema = False
        while retries > 0:
            if self._test_for_valid_schema_file():
                break
            has_new_schema = True
            self._generate_schema()
            retries -= 1

        if not self._test_for_valid_models_file() or has_new_schema:
            models_path.unlink(missing_ok=True)
            self._generate_models()

    def _test_for_valid_schema_file(self) -> bool:
        schema_path = self._get_current_schema_path()
        if not schema_path.exists() or self._is_schema_outdated(schema_path):
            return False
        try:
            schema_dict = json.load(schema_path.open())
        except json.JSONDecodeError:
            return False
        if not schema_dict or schema_dict.get("data") is None or schema_dict.get("errors"):
            return False
        return True

    def _test_for_valid_models_file(self) -> bool:
        models_path = self._get_current_models_path()
        if not models_path.exists():
            return False
        if models_path.stat().st_size > 1024 * 1024:
            return True
        _logger.warning(f"Model file {models_path} is empty or too small")
        return False

    def _get_current_schema_path(self) -> Path:
        return Path(__file__).parent / "generated" / f"shopify_{self.api_version}.json"

    @staticmethod
    def _get_current_models_path() -> Path:
        return Path(__file__).parent / "generated" / "shopify.py"

    @staticmethod
    def _is_schema_outdated(schema_file: Path) -> bool:
        return time.time() - schema_file.stat().st_mtime > datetime.timedelta(weeks=1).total_seconds()

    def _get_endpoint(self) -> HTTPEndpoint:
        if self._endpoint:
            return self._endpoint

        if not (self.store_url and self.api_version and self.api_token):
            raise ValueError(
                f"Shopify client setting(s) not found: {'store url' if not self.store_url else ''} {'api version' if not self.api_version else ''} {'api token' if not self.api_token else ''}"
            )

        headers = {"X-Shopify-Access-Token": self.api_token}
        ShopifyClient._endpoint = HTTPEndpoint(self.endpoint_url, headers, timeout=30)

        return self._endpoint

    def _generate_schema(self) -> None:
        schema_path = self._get_current_schema_path()
        _logger.info(f"Generating schema for Shopify API version {self.api_version}")
        endpoint = self._get_endpoint()
        response_data = endpoint(introspection.query, introspection.variables(include_deprecated=False))
        response_str = json.dumps(response_data, sort_keys=True, indent=2, default=str)
        # noinspection HttpUrlsUsage
        response_str = response_str.replace("http://", "https://")
        schema_path.write_text(response_str)

    def _generate_models(self) -> None:

        schema_path = self._get_current_schema_path()
        models_path = self._get_current_models_path()
        schema_data = json.load(schema_path.open())
        schema = schema_data.get("data", {}).get("__schema", {})

        generator = CodeGen("shopify_schema", schema, models_path.open("w").write, docstrings=False)
        generator.write()

    def execute(self, operation: Operation, variables: dict[str, Any] = None):
        endpoint = self._get_endpoint()
        result = endpoint(operation, variables)

        if "errors" in result:
            raise ValueError(f"Shopify GraphQL query failed: {result['errors']}")

        return result

    def _overwrite_settings_from_dotenv(self) -> None:
        load_dotenv()
        for key, val in os.environ.items():
            if key.startswith("SHOPIFY_") and key.endswith("_TEST"):
                odoo_key = key.replace("_TEST", "").replace("SHOPIFY_", "shopify.").lower()
                self.env["ir.config_parameter"].sudo().set_param(odoo_key, val)

    def _settings_from_db(self) -> None:
        ir_config_parameter = self.env["ir.config_parameter"].sudo()
        self.store_url_key = ir_config_parameter.get_param("shopify.store_url_key")
        self.api_version = ir_config_parameter.get_param("shopify.api_version")
        self.api_token = ir_config_parameter.get_param("shopify.api_token")
        self.store_url = f"https://{self.store_url_key}.myshopify.com"
        self.endpoint_url = f"{self.store_url}/admin/api/{self.api_version}/graphql.json"
