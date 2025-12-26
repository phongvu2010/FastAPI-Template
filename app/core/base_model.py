from datetime import datetime
from sqlalchemy import DateTime, func
from sqlmodel import Field, SQLModel
from typing import Optional


class Base(SQLModel):
    pass


class TimestampMixin(SQLModel):
    """
    Mixin to provide self-updating 'created_at' and 'updated_at' columns.
    """
    created_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.now(),
            "nullable": False,
        },
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),
            "nullable": False,
        },
    )
