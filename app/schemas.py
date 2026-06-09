from pydantic import BaseModel
from typing import Optional

class AppealCreate(BaseModel):
    topic: str
    message: str
    is_anonymous: bool = False
    sender_name: Optional[str] = None
    email: Optional[str] = None
