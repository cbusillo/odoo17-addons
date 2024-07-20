import requests

from .exceptions import ShopifyGraphQLException


class ShopifyGraphQLClient:
    def __init__(self, shop_url: str, access_token: str) -> None:
        self.shop_url = shop_url
        self.access_token = access_token
        self.endpoint = f"https://{self.shop_url}/admin/api/2023-10/graphql.json"

    def execute(self, query: str, variables: str | None = None) -> dict:
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }
        payload: dict = {"query": query, "variables": variables or {}}

        response = requests.post(self.endpoint, json=payload, headers=headers)

        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                raise ShopifyGraphQLException(result["errors"])
            return result["data"]
        else:
            raise ShopifyGraphQLException(f"Query failed with status code: {response.status_code}")
