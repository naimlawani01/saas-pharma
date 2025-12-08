from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """Réponse de token JWT."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Secondes


class TokenPayload(BaseModel):
    """Payload du token JWT."""
    sub: Optional[str] = None
    role: Optional[str] = None
    pharmacy_id: Optional[int] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Requête de rafraîchissement de token."""
    refresh_token: str
