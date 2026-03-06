from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator

Role = Literal["owner", "resident", "prospective", "industry", "other"]
Interest = Literal["market", "community", "investment", "maintenance", "regulations", "listings"]


class SubscribeRequest(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[Role] = None
    interests: Optional[list[Interest]] = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_and_nullify(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None


class SubscribeResponse(BaseModel):
    message: str
    email: str


class UnsubscribeRequest(BaseModel):
    email: EmailStr


class SubscriberRecord(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: Optional[str]
    interests: Optional[list]
    subscribed_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


# --- Contact schemas ---

class ContactRequest(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: EmailStr
    subject: Optional[str] = None
    message: str

    @field_validator("first_name", "last_name", "message", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None


class ContactResponse(BaseModel):
    message: str


# --- Auth schemas ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
