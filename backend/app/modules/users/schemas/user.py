from pydantic import BaseModel, EmailStr, Field, ConfigDict

from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=8
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )
    id: int
    email: str
    is_active: bool
    created_at: datetime
