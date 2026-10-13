from pydantic import BaseModel, Field


class StockAdjustment(BaseModel):
    quantity: int = Field(gt=0)
