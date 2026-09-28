import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrandCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100
    )

    slug: str = Field(
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

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        value = value.strip().lower()

        if not re.fullmatch(
            r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
            value
        ):
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

    slug: str | None = Field(
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


class BrandResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    name: str
    slug: str
