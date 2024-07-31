import logging
import os
import time
from functools import lru_cache
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
from odoo import models, api, fields
from odoo.api import Environment
from odoo.modules import module
from pydantic import BaseModel, ValidationError
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

_logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ShopifyConfig(models.Model):
    _name = "shopify.config"
    _description = "Shopify Config and Rate Limiting"

    store_url_key = fields.Char()
    api_version = fields.Char()
    api_token = fields.Char()
    available_points = fields.Integer(default=2000)
    last_leak_time = fields.Integer(default=lambda self: int(time.time()))
    max_bucket_size = fields.Integer(default=2000)
    leak_rate = fields.Integer(default=100)

    @property
    def store_url(self) -> str:
        return f"https://{self.store_url_key}.myshopify.com"

    @property
    def endpoint_url(self) -> str:
        return f"{self.store_url}/admin/api/{self.api_version}/graphql.json"

    @api.model
    def get_config(self, from_dot_env: bool) -> "odoo.model.shopify_config":
        if from_dot_env:
            self.load_from_dotenv()

        ir = self.env["ir.config_parameter"].sudo()
        store_url_key = ir.get_param("shopify.store_url_key")
        config = self.search([("store_url_key", "=", store_url_key)], limit=1)
        if not config:
            vals: "odoo.values.shopify_config" = {
                "store_url_key": store_url_key,
                "api_version": ir.get_param("shopify.api_version"),
                "api_token": ir.get_param("shopify.api_token"),
            }
            config = self.create(vals)
        return config

    @api.model
    def load_from_dotenv(self) -> None:
        load_dotenv()
        for key, val in os.environ.items():
            if key.startswith("SHOPIFY_") and key.endswith("_TEST"):
                odoo_key = key.replace("_TEST", "").replace("SHOPIFY_", "shopify.").lower()
                self.env["ir.config_parameter"].sudo().set_param(odoo_key, val)


class ShopifyClientService:
    _session: Session | None = None

    def __init__(self, env: Environment, from_dot_env: bool = False) -> None:
        self.env = env
        self.from_dot_env = from_dot_env

    @property
    def endpoint_url(self) -> str:
        return self._get_config().endpoint_url

    def _get_config(self) -> ShopifyConfig:
        return self.env["shopify.config"].get_config(from_dot_env=self.from_dot_env)

    def _get_session(self) -> Session:
        if not self._session:
            config = self._get_config()
            self._session = requests.Session()
            retry_strategy = Retry(
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "POST"],
                backoff_factor=0.1,
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("https://", adapter)
            self._session.headers.update(
                {
                    "X-Shopify-Access-Token": config.api_token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                }
            )
        return self._session

    def execute_query(
        self,
        query_type: str,
        query_name: str,
        variables: dict[str, Any] | None = None,
        estimated_cost: int = 500,
        return_pydantic_model: bool = True,
        pydantic_model: type[T] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | T | list[T]:
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

    def _send_request(self, payload: dict[str, Any], estimated_cost: int) -> dict[str, Any]:
        config = self._get_config()
        session = self._get_session()
        try:
            response = session.post(config.endpoint_url, json=payload)
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
            config = self._get_config()
            config.available_points = cost_info["throttleStatus"]["currentlyAvailable"]
            if actual_cost > estimated_cost:
                self._wait_for_bucket(actual_cost - estimated_cost)
            _logger.debug(f"Query cost: {cost_info}")
            throttle_status = cost_info["throttleStatus"]
            if config.max_bucket_size != throttle_status["maximumAvailable"]:
                config.max_bucket_size = throttle_status["maximumAvailable"]
            if config.leak_rate != throttle_status["restoreRate"]:
                config.leak_rate = throttle_status["restoreRate"]
            config.available_points = throttle_status["currentlyAvailable"]
        except KeyError:
            _logger.warning("No throttle status found in query cost info: {cost_info}")

    def _leak_bucket(self) -> None:
        config = self._get_config()
        now = int(time.time())
        time_passed = now - config.last_leak_time
        leaked_points = time_passed * config.leak_rate
        config.available_points = min(config.max_bucket_size, config.available_points + leaked_points)
        config.last_leak_time = now

    def _wait_for_bucket(self, cost: float) -> None:
        config = self._get_config()
        while config.available_points < cost:
            self._leak_bucket()
            if config.available_points < cost:
                sleep_time = min((cost - config.available_points) / config.leak_rate, 0.1)
                time.sleep(sleep_time)
        config.available_points -= cost

    @lru_cache
    def _load_query_file(self, query_type: str) -> DocumentNode:
        query_type_path = self._get_graphql_path() / f"shopify_{query_type}.graphql"
        if not query_type_path.exists():
            raise ValueError(f"Query type file {query_type_path} not found")
        return parse(query_type_path.read_text())

    @lru_cache(maxsize=1)
    def _get_graphql_path(self) -> Path:
        module_path_str = self._get_module_path()
        return Path(module_path_str) / "graphql"

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_module_path() -> Path:
        module_path_str = module.get_module_path("product_connect")
        if not module_path_str or not isinstance(module_path_str, str):
            raise ValueError("Module path not found")
        return Path(module_path_str)

    @lru_cache
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


class ShopifyClient(models.TransientModel):
    _name = "shopify.client"
    _description = "Shopify GraphQL Client"

    from_dot_env = fields.Boolean(default=False)

    @api.model
    def create(self, vals: "odoo.values.shopify_client") -> "odoo.model.shopify_client":
        result = super().create(vals)

        return result

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
        client = ShopifyClientService(self.env, self.from_dot_env)
        return client.execute_query(
            query_type, query_name, variables, estimated_cost, return_pydantic_model, pydantic_model
        )

    def get_first_location(self) -> str:
        from odoo.addons.product_connect.services.models.shopify_product import Location

        location = self.execute_query("store", "GetLocation", pydantic_model=Location)
        return location.id

    @property
    def endpoint_url(self) -> str:
        client = ShopifyClientService(self.env, self.from_dot_env)
        return client.endpoint_url
