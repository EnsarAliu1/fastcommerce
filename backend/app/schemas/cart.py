from pydantic import BaseModel, ConfigDict, Field


class CartCreate(BaseModel):
    pass


class CartItemCreate(BaseModel):
    variant_id: int
    quantity: int = Field(gt=0)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cart_id: int
    variant_id: int
    quantity: int


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    items: list[CartItemResponse]
