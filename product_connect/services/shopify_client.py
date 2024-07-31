import logging
import os
import time
from pathlib import Path
from typing import Any, TypeVar

import requests
from dotenv import load_dotenv
from graphql import (
    parse,
    print_ast,
    DocumentNode,
    OperationDefinitionNode,
    FragmentDefinitionNode,
)
from odoo import models, api, fields, tools
from odoo.modules import module
from pydantic import BaseModel, ValidationError
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

_logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ShopifyClient(models.TransientModel):
    _name = "shopify.client"
    _description = "Shopify GraphQL API Client"

    store_url_key = fields.Char()
    api_version = fields.Char()
    api_token = fields.Char()
    store_url = fields.Char()
    endpoint_url = fields.Char()

    _cls_session: Session | None = None
    _cls_session_available_points = 2000
    _cls_session_last_leak_time = int(time.time())
    _cls_session_max_bucket_size = 2000
    _cls_session_leak_rate = 100

    @api.model_create_multi
    def create(self, vals_list: list["odoo.values.shopify_client"]) -> "ShopifyClient":
        clients = super().create(vals_list)
        for client in clients:
            client._settings_from_db()
            client._create_session()
        return clients

    def ensure_session(self) -> Session:
        if not ShopifyClient._cls_session:
            self._create_session()
        if not ShopifyClient._cls_session:
            raise ValueError("Session not found")
        return ShopifyClient._cls_session

    def get_first_location(self) -> str:
        from odoo.addons.product_connect.services.models.shopify_product import Location

        location = self.execute_query("store", "GetLocation", pydantic_model=Location)
        return location.id

    @api.model
    def execute_query(
        self,
        query_type: str,
        query_name: str,
        variables: dict[str, Any] | None = None,
        estimated_cost: int = 500,
        return_pydantic_model: bool = True,
        pydantic_model: type[T] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | T | list[T]:
        self.ensure_session()
        query_document = self._load_query_file(query_type)
        query = self._get_query_and_fragments(query_document, query_name)
        payload = {"query": query, "variables": variables or {}}

        self._wait_for_bucket(estimated_cost)
        result = self._send_request(payload, estimated_cost)
        flat_result = self._flatten_graphql_response(result)
        if return_pydantic_model:
            return self._convert_to_pydantic_model(flat_result, pydantic_model)
        return flat_result

    @staticmethod
    def _convert_to_pydantic_model(data: dict[str, Any], model: type[T] | None) -> T | list[T]:
        if not model:
            raise ValueError("Model type not provided (required for Pydantic conversion)")
        try:
            if isinstance(data, list):
                return [model.model_validate(item) for item in data]
            return model.model_validate(data, from_attributes=True)
        except ValidationError as error:
            raise ValueError(f"Data validation failed: {error}")

    def _create_session(self) -> Session:
        retry_strategy = Retry(
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
            backoff_factor=0.1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        ShopifyClient._cls_session = Session()
        ShopifyClient._cls_session.mount("https://", adapter)
        ShopifyClient._cls_session.headers.update(
            {
                "X-Shopify-Access-Token": self.api_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
        )
        return ShopifyClient._cls_session

    def _send_request(self, payload: dict[str, Any], estimated_cost: int) -> dict[str, Any]:
        try:
            response = ShopifyClient._cls_session.post(self.endpoint_url, json=payload)
            response.raise_for_status()
            result = response.json()
            _logger.debug(f"Query result: {result}")
            if "errors" in result:
                raise ValueError(
                    f"Shopify GraphQL query failed: {result['errors']}\nQuery: {payload.get('query')}\nVariables: {payload.get('variables')}"
                )
            self._handle_cost_info(result["extensions"]["cost"], estimated_cost)
            return result["data"]
        except (requests.exceptions.RequestException, ValueError) as error:
            raise ValueError(f"Shopify GraphQL query failed: {error}")

    def _handle_cost_info(self, cost_info: dict, estimated_cost: int) -> None:
        try:
            actual_cost = cost_info["requestedQueryCost"]
            if actual_cost > estimated_cost:
                self._wait_for_bucket(actual_cost - estimated_cost)
            _logger.debug(f"Query cost: {cost_info}")
            throttle_status = cost_info["throttleStatus"]
            ShopifyClient._cls_session_max_bucket_size = throttle_status["maximumAvailable"]
            ShopifyClient._cls_session_leak_rate = throttle_status["restoreRate"]
            ShopifyClient._cls_session_available_points = throttle_status["currentlyAvailable"]
        except KeyError:
            _logger.warning("No throttle status found in query cost info: {cost_info}")

    def _leak_bucket(self) -> None:
        now = int(time.time())
        time_passed = now - ShopifyClient._cls_session_last_leak_time
        leaked_points = time_passed * ShopifyClient._cls_session_leak_rate
        ShopifyClient._cls_session_available_points = min(
            ShopifyClient._cls_session_max_bucket_size, ShopifyClient._cls_session_available_points + leaked_points
        )
        ShopifyClient._cls_session_last_leak_time = now

    def _wait_for_bucket(self, cost: float) -> None:
        while ShopifyClient._cls_session_available_points < cost:
            self._leak_bucket()
            if ShopifyClient._cls_session_available_points < cost:
                sleep_time = min(
                    (cost - ShopifyClient._cls_session_available_points) / ShopifyClient._cls_session_leak_rate, 0.1
                )
                time.sleep(sleep_time)
        ShopifyClient._cls_session_available_points -= cost

    def _overwrite_settings_from_dotenv(self) -> None:
        load_dotenv()
        for key, val in os.environ.items():
            if key.startswith("SHOPIFY_") and key.endswith("_TEST"):
                odoo_key = key.replace("_TEST", "").replace("SHOPIFY_", "shopify.").lower()
                self.env["ir.config_parameter"].sudo().set_param(odoo_key, val)

    def _settings_from_db(self) -> None:
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        self.store_url_key = IrConfigParameter.get_param("shopify.store_url_key")
        self.api_version = IrConfigParameter.get_param("shopify.api_version")
        self.api_token = IrConfigParameter.get_param("shopify.api_token")
        self.store_url = f"https://{self.store_url_key}.myshopify.com"
        self.endpoint_url = f"{self.store_url}/admin/api/{self.api_version}/graphql.json"

    def _load_query_file(self, query_type: str) -> DocumentNode:
        query_type_path = self._get_graphql_path() / f"shopify_{query_type}.graphql"
        if not query_type_path.exists():
            raise ValueError(f"Query type file {query_type_path} not found")
        return parse(query_type_path.read_text())

    def _get_graphql_path(self) -> Path:
        module_path_str = self._get_module_path()
        return Path(module_path_str) / "graphql"

    @staticmethod
    def _get_module_path() -> Path:
        module_path_str = module.get_module_path("product_connect")
        if not module_path_str or not isinstance(module_path_str, str):
            raise ValueError("Module path not found")
        return Path(module_path_str)

    @tools.ormcache("document", "query_name")
    def _get_query_and_fragments(self, document: DocumentNode, query_name: str) -> str:
        query = None
        fragments = []

        for definition in document.definitions:
            if (
                isinstance(definition, OperationDefinitionNode)
                and definition.name
                and definition.name.value == query_name
            ):
                query = print_ast(definition)
            elif isinstance(definition, FragmentDefinitionNode):
                fragments.append(print_ast(definition))

        if not query:
            raise ValueError(f"Query '{query_name}' not found in the document")

        return f"{query}\n\n{''.join(fragments)}"

    def _flatten_graphql_response(
        self, data: list[dict[str, Any]] | dict[str, Any]
    ) -> list[dict[str, Any]] | dict[str, Any]:
        if isinstance(data, dict):
            if len(data) == 1 and isinstance(next(iter(data.values())), dict):
                return self._flatten_graphql_response(next(iter(data.values())))
            if "edges" in data and isinstance(data["edges"], list):
                return [self._flatten_graphql_response(edge["node"]) for edge in data["edges"] if "node" in edge]
            return {k: self._flatten_graphql_response(v) for k, v in data.items() if k not in ["edges", "node"]}
        elif isinstance(data, list):
            return [self._flatten_graphql_response(item) for item in data]
        else:
            return data
