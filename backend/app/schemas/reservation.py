from pydantic import BaseModel, Field


class StockReservationCreate(BaseModel):
    quantity: int = Field(gt=0)
