from __future__ import annotations

import enum
from urllib.parse import urlparse

from pydantic import BaseConfig, BaseModel


# https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/api_model.py


class Schema(BaseModel):
    class Config(BaseConfig):
        orm_mode = True


class NameSchema(Schema):
    name: str


class IdNameSchema(Schema):
    id: int
    name: str


class IdSchema(Schema):
    id: int


class GenderEnum(str, enum.Enum):
    male = "Male"
    female = "Female"


class MaritalStatusEnum(str, enum.Enum):
    Single = "Single"
    Married = "Married"
    Divorced = "Divorced"
    Others = "Others"


# class PresignFormField(str):
#     @classmethod
#     def __get_validators__(cls):
#         return [lambda v: strip_url(v)]
