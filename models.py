from datetime import date, time, datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field

# Base Models (for database schema representation if using ORM)
# If not using SQLAlchemy ORM, these directly represent table rows for data transfer

class MenuItemBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    price: float = Field(..., ge=0) # Greater than or equal to 0
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = None
    is_available: bool = True

class MenuItemCreate(MenuItemBase):
    pass # No extra fields for creation, inherits from base

class MenuItemUpdate(MenuItemBase):
    name: Optional[str] = Field(None, max_length=255)
    price: Optional[float] = Field(None, ge=0)
    # Make all fields optional for update

class MenuItemResponse(MenuItemBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Changed from orm_mode = True for Pydantic v2

class UserBase(BaseModel):
    username: str = Field(..., max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: Literal["admin", "customer"] = "customer"

class UserResponse(UserBase):
    id: UUID
    role: Literal["admin", "customer"]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ReservationBase(BaseModel):
    customer_name: str = Field(..., max_length=255)
    customer_email: str = Field(..., max_length=255)
    customer_phone: str = Field(..., max_length=50)
    reservation_date: date
    reservation_time: time
    number_of_guests: int = Field(..., ge=1)
    status: Literal['pending', 'confirmed', 'cancelled', 'completed', 'no_show'] = 'pending'
    notes: Optional[str] = None

class ReservationCreate(ReservationBase):
    pass # No extra fields for creation

class ReservationUpdate(ReservationBase):
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=50)
    reservation_date: Optional[date] = None
    reservation_time: Optional[time] = None
    number_of_guests: Optional[int] = Field(None, ge=1)
    status: Optional[Literal['pending', 'confirmed', 'cancelled', 'completed', 'no_show']] = None
    notes: Optional[str] = None
    # Make all fields optional for update

class ReservationResponse(ReservationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# For Auth (Login)
class Token(BaseModel):
    access_token: str
    token_type: str
    user_role: Literal["admin", "customer"]

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[Literal["admin", "customer"]] = None

class UserInDB(UserResponse):
    hashed_password: str

# General Error Response
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None