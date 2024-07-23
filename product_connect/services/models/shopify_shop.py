from typing import Optional, TYPE_CHECKING

from pydantic import HttpUrl

from .shopify_base import ShopifyBase

if TYPE_CHECKING:
    from .shopify_base import HasMetafields


class Domain(ShopifyBase):
    id: Optional[str] = None
    host: Optional[str] = None
    url: Optional[HttpUrl] = None


class Shop(ShopifyBase, HasMetafields):
    id: Optional[str] = None
    name: Optional[str] = None
    primary_domain: Optional[Domain] = None
