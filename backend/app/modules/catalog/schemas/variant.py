import re
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductVariantReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int

    sku: str = Field(
        min_length=3,
        max_length=50
    )

    price: Decimal = Field(
        gt=0
    )

    size: str | None = Field(
        default=None,
        max_length=100
    )

    color: str | None = Field(
        default=None,
        max_length=100
    )

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


class ProductVariantCreate(ProductVariantReplace):
    stock_quantity: int = Field(
        default=0,
        ge=0
    )


class ProductVariantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int | None = None

    sku: str | None = Field(
        default=None,
        min_length=3,
        max_length=50
    )

    price: Decimal | None = Field(
        default=None,
        gt=0
    )

    size: str | None = Field(
        default=None,
        max_length=100
    )

    color: str | None = Field(
        default=None,
        max_length=100
    )

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


class ProductVariantResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    product_id: int
    sku: str
    price: Decimal
    stock_quantity: int
    size: str | None
    color: str | None
    is_in_stock: bool
