import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TimeStampedModel(Base):
    """Abstract base class with UUID primary key and automatic timestamps."""
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)
