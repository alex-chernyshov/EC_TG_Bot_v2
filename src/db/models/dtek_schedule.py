from sqlalchemy import Column, Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB

from src.db.models.base import Base


class DtekSchedule(Base):
    __tablename__ = "dtek_schedules"
    __table_args__ = (UniqueConstraint("group_code", "day"),)
    __mapper_args__ = {"eager_defaults": True}

    id = Column(Integer, primary_key=True)

    group_code = Column(String, nullable=False, index=True)  # e.g. "2.2"
    day = Column(Date, nullable=False)  # Kyiv calendar day
    hours = Column(JSONB, nullable=False)  # {"1": "yes|no|first|second", ..., "24": ...}; "1" is 00-01
    site_updated = Column(String, nullable=False)  # DTEK's own "last updated" text, shown to users

    date_fetched = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
