import re
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.brand import BrandResponse
from app.schemas.category import CategoryResponse
from app.schemas.variant import ProductVariantResponse


class ProductCreate(BaseModel):
    category_id: int
    brand_id: int

    name: str = Field(
        min_length=2,
        max_length=100
    )

    description: str = Field(
        max_length=1000
    )

    price: Decimal = Field(
        gt=0
    )

    sku: str = Field(
        min_length=3,
        max_length=50
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, value: str) -> str:
        value = value.strip().upper()

        if not re.fullmatch(
            r"^[A-Z]{3}-\d{3}$",
            value
        ):
            raise ValueError(
                "SKU must have format ABC-123"
            )

        return value


class ProductUpdate(BaseModel):
    category_id: int | None = None
    brand_id: int | None = None

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    description: str | None = Field(
        default=None,
        max_length=1000
    )

    price: Decimal | None = Field(
        default=None,
        gt=0
    )

    sku: str | None = Field(
        default=None,
        min_length=3,
        max_length=50
    )

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str | None
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

    @field_validator("sku")
    @classmethod
    def validate_sku(
        cls,
        value: str | None
    ) -> str | None:
        if value is None:
            return value

        value = value.strip().upper()

        if not re.fullmatch(
            r"^[A-Z]{3}-\d{3}$",
            value
        ):
            raise ValueError(
                "SKU must have format ABC-123"
            )

        return value


class ProductResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    category_id: int
    brand_id: int
    name: str
    description: str
    price: Decimal
    sku: str

    category: CategoryResponse
    brand: BrandResponse
    variants: list[ProductVariantResponse]

    is_in_stock: bool
