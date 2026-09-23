from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

import re


class ProductCreate(BaseModel):

    category_id: int

    brand_id: int

    name: str = Field(
        min_length=2,
        max_length=100
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

    description: str = Field(
        max_length=1000
    )

    price: Decimal = Field(
        gt=0
    )

    in_stock: bool = True

    sku: str = Field(
        min_length=3,
        max_length=50
    )

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, value: str) -> str:
        value = value.strip().upper()

        if not re.fullmatch(r"^[A-Z]{3}-\d{3}$", value):
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

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

    description: str | None = Field(
        default=None,
        max_length=1000
    )

    price: Decimal | None = Field(
        default=None,
        gt=0
    )

    in_stock: bool | None = None

    sku: str | None = Field(
        default=None,
        min_length=3,
        max_length=50
    )

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, value: str) -> str:
        value = value.strip().upper()

        if not re.fullmatch(r"^[A-Z]{3}-\d{3}$", value):
            raise ValueError(
                "SKU must have format ABC-123"
            )

        return value


class CategoryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    name: str
    slug: str


class BrandResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    name: str
    slug: str


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
    in_stock: bool
    sku: str
    category: CategoryResponse


class CategoryCreate(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=100
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

    slug: str = Field(
        min_length=3,
        max_length=50
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        value = value.strip().lower()

        if not re.fullmatch(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value):
            raise ValueError(
                "Slug must contain lowercase letters, numbers and hyphens"
            )

        return value


class CategoryUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
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
            raise ValueError(
                "Name cannot be empty"
            )

        return value

    slug: str | None = Field(
        default=None,
        min_length=3,
        max_length=50
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(
        cls,
        value: str | None
    ) -> str | None:
        if value is None:
            return value

        value = value.strip().lower()

        if not re.fullmatch(
            r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
            value
        ):
            raise ValueError(
                "Slug must contain lowercase letters, numbers and hyphens"
            )

        return value


class BrandCreate(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=100
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

    slug: str = Field(
        min_length=3,
        max_length=50
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        value = value.strip().lower()

        if not re.fullmatch(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value):
            raise ValueError(
                "Slug must contain lowercase letters, numbers and hyphens"
            )

        return value


class BrandUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    field_validator("name")

    @classmethod
    def validate_name(
        cls,
        value: str | None
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError(
                "Name cannot be empty"
            )

        return value

    slug: str | None = Field(
        default=None,
        min_length=3,
        max_length=50
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(
        cls,
        value: str | None
    ) -> str | None:
        if value is None:
            return value

        value = value.strip().lower()

        if not re.fullmatch(
            r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
            value
        ):
            raise ValueError(
                "Slug must contain lowercase letters, numbers and hyphens"
            )

        return value
