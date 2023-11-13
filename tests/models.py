from datetime import date

from tests.database import database
from unqdantic import Document

from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    money: float = 200
    birthday: date = Field(default_factory=date.today)


class User(Document):
    name: str
    age: int = 18
    info: UserInfo

    class Meta:
        db = database
        name = "user"
