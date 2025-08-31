from pydantic import BaseModel
from typing import Optional, Union

class UserSchema(BaseModel):
    id: Union[str, int]
    name: str
    email: str
    picture: Optional[str] = None