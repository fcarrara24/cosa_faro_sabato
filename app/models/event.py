from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class EventType(str, Enum):
    CONCERT = "concert"
    CLUB = "club"
    LIVE_MUSIC = "live_music"
    FESTIVAL = "festival"
    THEATER = "theater"
    EXHIBITION = "exhibition"
    SPORT = "sport"
    OTHER = "other"


class EventSource(str, Enum):
    EVENTBRITE = "eventbrite"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    VENUE_WEBSITE = "venue_website"
    MEETUP = "meetup"
    DICE = "dice"
    VIVABERGAMO = "vivabergamo"
    BERGAMOEVENTS = "bergamoevents"
    LOMBARDIA_EVENTI = "lombardia_eventi"


class Event(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    date: datetime
    time: Optional[str] = Field(None, max_length=10)
    location: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    type: Optional[EventType] = EventType.OTHER
    price: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    source: EventSource
    link: str = Field(..., min_length=1, max_length=500)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EventCreate(BaseModel):
    title: str
    date: datetime
    time: Optional[str] = None
    location: str
    city: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type: Optional[EventType] = EventType.OTHER
    price: Optional[str] = None
    description: Optional[str] = None
    source: EventSource
    link: str


class EventUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[datetime] = None
    time: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type: Optional[EventType] = None
    price: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None


class EventResponse(BaseModel):
    id: int
    title: str
    date: datetime
    time: Optional[str]
    location: str
    city: str
    latitude: Optional[float]
    longitude: Optional[float]
    type: Optional[EventType]
    price: Optional[str]
    description: Optional[str]
    source: EventSource
    link: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EventSearchParams(BaseModel):
    city: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    type: Optional[EventType] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    location: Optional[str] = None
    source: Optional[EventSource] = None
    weekend_only: bool = False
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
