import datetime as dt

from sqlalchemy import Enum, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.apod import MediaType
from app.models.base import Base, TimestampMixin


class Brief(TimestampMixin, Base):
    __tablename__ = "briefs"
    __table_args__ = (
        Index(
            "ix_briefs_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(Text)
    media_type: Mapped[MediaType] = mapped_column(
        Enum(
            MediaType, native_enum=False, values_callable=lambda e: [m.value for m in e]
        )
    )
    hd_url: Mapped[str | None] = mapped_column(Text)
    facts: Mapped[list[str] | None] = mapped_column(JSONB)
    explanation: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    credit: Mapped[str | None] = mapped_column(Text)
    simple_explanation: Mapped[str | None] = mapped_column(Text)
