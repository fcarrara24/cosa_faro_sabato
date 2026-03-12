from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Index
from sqlalchemy.sql import func
from app.database.db import Base
from app.models.event import EventType, EventSource


class EventDB(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    date = Column(DateTime, nullable=False)
    time = Column(String(10), nullable=True)
    location = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    type = Column(String(50), nullable=True)
    price = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    source = Column(String(50), nullable=False)
    link = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_date_city', 'date', 'city'),
        Index('idx_city_type', 'city', 'type'),
        Index('idx_source_date', 'source', 'date'),
        Index('idx_location_date', 'location', 'date'),
    )

    def __repr__(self):
        return f"<EventDB(id={self.id}, title='{self.title}', date='{self.date}', location='{self.location}')>"
