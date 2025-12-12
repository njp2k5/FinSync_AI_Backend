from pydantic import BaseModel

class SaveProfileIn(BaseModel):
    phone: str
