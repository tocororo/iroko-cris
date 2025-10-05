from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    roles: List[str] = []  # Add roles here
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class UserWithRoles(UserResponse):
    # This can now be the same as UserResponse or removed if not needed
    pass

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permissions: List[str] = []

class RoleResponse(RoleBase):
    id: UUID
    permissions: List[str]
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[UUID] = None

class TokenUser(BaseModel):
    """User data extracted from JWT token"""
    id: UUID
    email: str
    roles: List[str]
    is_superuser: bool
    
    class Config:
        from_attributes = True
        
class CaptchaResponse(BaseModel):
    captcha_id: str
    captcha_image: str  # Base64 encoded image
    expires_at: datetime

    class Config:
        from_attributes = True