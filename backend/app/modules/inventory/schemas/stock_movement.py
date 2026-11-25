from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    variant_id: int
    admin_id: int | None
    movement_type: Literal["manual_increase", "manual_decrease"]
    quantity_delta: int
    stock_before: int
    stock_after: int
    reason: str | None
    created_at: datetime
