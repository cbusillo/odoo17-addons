from datetime import datetime
from enum import Enum
from typing import Optional, TypeAlias

from pydantic import BaseModel, ConfigDict, Json


def to_camel(string: str) -> str:
    words = string.split("_")
    return words[0].lower() + "".join(word.capitalize() for word in words[1:])


#
# class Id(BaseModel):
#
#     model_config = ConfigDict(
#         populate_by_name=True,
#         extra="ignore",
#         alias_generator=to_camel,
#         from_attributes=True,
#     )
#     gid: Optional[str] = Field(None, alias="id")
#
#     # noinspection PyMethodParameters
#     @field_validator("gid", mode="before")
#     def validate_gid(cls, v: Any) -> Optional[str]:
#         if isinstance(v, str):
#             return v
#         elif isinstance(v, dict):
#             return v.get("id") or v.get("gid")
#         elif v is None:
#             return None
#         raise ValueError(f"Invalid ID format: {v}")
#
#     def __str__(self) -> str:
#         return self.gid if self.gid else ""
#
#     @property
#     def numeric_id(self) -> Optional[int]:
#         if self.gid:
#             match = re.search(r"/(\d+)$", self.gid)
#             return int(match.group(1)) if match else None
#         return None
#
#     @property
#     def resource_type(self) -> Optional[str]:
#         if self.gid:
#             match = re.search(r"gid://shopify/(\w+)/", self.gid)
#             return match.group(1) if match else None
#         return None
#
#     @classmethod
#     def from_parts(cls, resource_type: str, numeric_id: int) -> "Id":
#         return cls(id=f"gid://shopify/{resource_type}/{numeric_id}")


Id: TypeAlias = str


class ShopifyBase(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        alias_generator=to_camel,
        from_attributes=True,
    )


class HasCompareDigest(ShopifyBase):
    compare_digest: Optional[str]


class MetafieldDefinition(ShopifyBase):
    description: Optional[str] = None
    id: Optional[Id] = None
    key: Optional[str] = None
    metafields: Optional[list["Metafield"]] = None
    metafields_count: Optional[int] = None
    name: Optional[str] = None
    namespace: Optional[str] = None
    pinned_position: Optional[int] = None


class Metafield(HasCompareDigest):
    compare_digest: Optional[str] = None
    created_at: Optional[datetime] = None
    definition: Optional[MetafieldDefinition] = None
    description: Optional[str] = None
    id: Optional[Id] = None
    json_value: Optional[Json] = None
    key: Optional[str] = None
    namespace: Optional[str] = None
    type: Optional[str] = None
    updated_at: Optional[datetime] = None
    value: Optional[str] = None


class HasMetafields(ShopifyBase):
    metafield: Optional[Metafield] = None
    metafields: Optional[list[Metafield]] = None


class CountPrecision(Enum):
    at_least = "AT_LEAST"
    exact = "EXACT"


class Count(ShopifyBase):
    count: Optional[int] = None
    precision: Optional[CountPrecision] = None
