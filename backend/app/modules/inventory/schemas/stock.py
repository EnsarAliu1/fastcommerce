from pydantic import BaseModel, Field, field_validator, ConfigDict


class StockAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value
