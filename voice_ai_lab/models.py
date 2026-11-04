"""Keep example contacts synthetic; validation also applies to voice tools."""

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from voice_ai_lab.knowledge import COURSES


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=500)


class LeadInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=120)
    course_id: str
    consent: bool = Field(strict=True)
    request_id: UUID

    @field_validator("consent")
    @classmethod
    def explicit_consent(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Explicit consent is required")
        return value

    @field_validator("email")
    @classmethod
    def synthetic_email(cls, value: str) -> str:
        value = value.lower()
        if not re.fullmatch(r"[a-z0-9._+-]+@(?:example\.(?:com|org|net)|[a-z0-9.-]+\.test)", value):
            raise ValueError(
                "Use a fictional address at example.com, example.org, example.net or .test"
            )
        return value

    @field_validator("course_id")
    @classmethod
    def known_course(cls, value: str) -> str:
        if value not in COURSES:
            raise ValueError("Select a course_id from the sample catalog")
        return value
