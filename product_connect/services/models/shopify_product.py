from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from pydantic import HttpUrl

from .shopify_base import ShopifyBase, Count

if TYPE_CHECKING:
    from .shopify_base import HasMetafields, Id


class ProductStatus(Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DRAFT = "DRAFT"


class Location(HasMetafields):
    created_at: Optional[str] = None
    id: Optional[Id] = None
    inventory_level: Optional["InventoryLevel"] = None
    is_active: Optional[bool] = None
    name: Optional[str] = None
    updated_at: Optional[str] = None


class Media(ShopifyBase):
    alt: Optional[str] = None
    id: Optional[Id] = None


class Catalog(ShopifyBase):
    id: Optional[Id] = None
    title: Optional[str] = None


class Publication(ShopifyBase):
    auto_publish: Optional[bool] = None
    catalog: Optional[Catalog] = None
    id: Optional[Id] = None


class ResourcePublicationV2(ShopifyBase):
    isPublished: Optional[bool] = None
    publication: Optional[Publication] = None
    publish_date: Optional[datetime] = None


class Weight(ShopifyBase):
    value: Optional[float] = None


class InventoryItemMeasurement(ShopifyBase):
    id: Optional[Id] = None
    weight: Optional[Weight] = None


class MoneyV2(ShopifyBase):
    amount: Optional[str] = None


class InventoryQuantity(ShopifyBase):
    id: Optional[Id] = None
    name: Optional[str] = None
    quantity: Optional[int] = None
    updated_at: Optional[datetime] = None


class InventoryLevel(ShopifyBase):
    created_at: Optional[str] = None
    id: Optional[Id] = None
    item: Optional["InventoryItem"] = None
    location: Optional[Location] = None
    quantities: Optional[list[InventoryQuantity]] = None
    updated_at: Optional[str] = None


class InventoryItem(ShopifyBase):
    created_at: Optional[str] = None
    id: Optional[Id] = None
    inventory_history_url: Optional[HttpUrl] = None
    inventory_level: Optional[InventoryLevel] = None
    measurement: Optional[InventoryItemMeasurement] = None
    sku: Optional[str] = None
    unit_cost: Optional[MoneyV2] = None
    updated_at: Optional[datetime] = None
    variant: Optional["ProductVariant"] = None
    inventory_levels: Optional[list[InventoryLevel]] = None


class ProductVariant(HasMetafields):
    available_for_sale: Optional[bool] = None
    barcode: Optional[str] = None
    created_at: Optional[str] = None
    id: Optional[Id] = None
    image: Optional[Media] = None
    inventory_item: Optional[InventoryItem] = None
    inventory_quantity: Optional[int] = None
    price: Optional[str] = None
    product: Optional["Product"] = None
    sku: Optional[str] = None
    title: Optional[str] = None
    updated_at: Optional[str] = None
    media: Optional[list[Media]] = None


class Product(HasMetafields):
    id: Optional[Id] = None
    created_at: Optional[str] = None
    description_html: Optional[str] = None
    featured_image: Optional[Media] = None
    media_count: Optional[Count] = None
    online_store_preview_url: Optional[HttpUrl] = None
    online_store_url: Optional[HttpUrl] = None
    product_type: Optional[str] = None
    published_at: Optional[datetime] = None
    status: Optional[ProductStatus] = None
    title: Optional[str] = None
    total_inventory: Optional[int] = None
    updated_at: Optional[str] = None
    vendor: Optional[str] = None

    images: Optional[list[Media]] = None
    resource_publication_v2: Optional[ResourcePublicationV2] = None
    variants: Optional[list[ProductVariant]] = None
