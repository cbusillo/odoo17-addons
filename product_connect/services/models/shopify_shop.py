from typing import Optional

from pydantic import HttpUrl

from .shopify_base import ShopifyBase, HasMetafields


class Domain(ShopifyBase):
    id: Optional[str] = None
    host: Optional[str] = None
    url: Optional[HttpUrl] = None


class Shop(HasMetafields):
    id: Optional[str] = None
    name: Optional[str] = None
    primary_domain: Optional[Domain] = None
