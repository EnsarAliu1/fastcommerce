from pydantic import BaseModel, Field, ConfigDict

from datetime import datetime


class StockReservationCreate(BaseModel):
    quantity: int = Field(gt=0)


class StockReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    variant_id: int
    quantity: int
    status: str
    created_at: datetime
    expires_at: datetime
