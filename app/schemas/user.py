from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.ASSISTANT
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    pharmacy_id: Optional[int] = None
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserLogin(BaseModel):
    """Schéma de connexion - email OU username."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not v:
            raise ValueError("Le mot de passe est requis")
        return v


class PasswordChange(BaseModel):
    """Changement de mot de passe."""
    current_password: str
    new_password: str
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError("Le nouveau mot de passe doit contenir au moins 6 caractères")
        return v


class PasswordReset(BaseModel):
    """Demande de réinitialisation de mot de passe."""
    email: Optional[EmailStr] = None


class PasswordResetConfirm(BaseModel):
    """Confirmation de réinitialisation de mot de passe."""
    email: EmailStr
    code: str
    new_password: str
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError("Le nouveau mot de passe doit contenir au moins 6 caractères")
        return v


class UserInDB(UserBase):
    id: int
    pharmacy_id: Optional[int] = None
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(UserInDB):
    pass
