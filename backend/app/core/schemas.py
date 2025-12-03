"""
Base schema configuration with automatic snake_case to camelCase conversion
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    """Base model with automatic snake_case to camelCase field conversion"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allow both snake_case and camelCase when parsing
        from_attributes=True,  # Allow ORM model conversion
        json_encoders={
            # Add custom encoders if needed
        },
    )


class ResponseModel(CamelCaseModel):
    """Base model for API responses with camelCase fields"""


class DatabaseModel(BaseModel):
    """Base model for database operations (keeps snake_case)"""

    model_config = ConfigDict(from_attributes=True)
