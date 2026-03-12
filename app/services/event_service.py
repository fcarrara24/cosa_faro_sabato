from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from fastapi import HTTPException

from app.database.schema import EventDB
from app.models.event import Event, EventCreate, EventUpdate, EventSearchParams, EventType, EventSource, EventResponse
from app.parsers.event_parser import EventParser

import logging

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, db: Session):
        self.db = db
        self.parser = EventParser()

    def create_event(self, event_data: EventCreate) -> EventResponse:
        """Create a new event"""
        try:
            # Normalize the event data
            normalized_event = self.parser.normalize_event(Event(**event_data.dict()))
            if not normalized_event:
                raise HTTPException(status_code=400, detail="Invalid event data")
            
            # Check for duplicates
            if self._is_duplicate(normalized_event):
                raise HTTPException(status_code=409, detail="Event already exists")
            
            # Create database record
            db_event = EventDB(
                title=normalized_event.title,
                date=normalized_event.date,
                time=normalized_event.time,
                location=normalized_event.location,
                city=normalized_event.city,
                latitude=normalized_event.latitude,
                longitude=normalized_event.longitude,
                type=normalized_event.type.value if normalized_event.type else None,
                price=normalized_event.price,
                description=normalized_event.description,
                source=normalized_event.source.value,
                link=normalized_event.link
            )
            
            self.db.add(db_event)
            self.db.commit()
            self.db.refresh(db_event)
            
            logger.info(f"Created event: {db_event.title}")
            return self._db_to_response(db_event)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating event: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_events(self, params: EventSearchParams) -> Tuple[List[EventResponse], int]:
        """Get events with advanced filtering and search"""
        try:
            query = self.db.query(EventDB)
            
            # Apply filters
            query = self._apply_filters(query, params)
            
            # Get total count
            total = len(query.all())  # Simplified for SQLite
            
            # Apply ordering and pagination
            query = query.order_by(EventDB.date.desc())
            query = query.offset(params.offset).limit(params.limit)
            
            events = query.all()
            
            return [self._db_to_response(event) for event in events], total
            
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            # Return empty result if database is empty or has issues
            return [], 0

    def get_event_by_id(self, event_id: int) -> EventResponse:
        """Get a specific event by ID"""
        event = self.db.query(EventDB).filter(EventDB.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return self._db_to_response(event)

    def update_event(self, event_id: int, event_data: EventUpdate) -> EventResponse:
        """Update an existing event"""
        try:
            event = self.db.query(EventDB).filter(EventDB.id == event_id).first()
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            # Update fields
            update_data = event_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(event, field):
                    if field == 'type' and value:
                        setattr(event, field, value.value)
                    elif field == 'source' and value:
                        setattr(event, field, value.value)
                    else:
                        setattr(event, field, value)
            
            self.db.commit()
            self.db.refresh(event)
            
            logger.info(f"Updated event: {event.title}")
            return self._db_to_response(event)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating event: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def delete_event(self, event_id: int) -> bool:
        """Delete an event"""
        try:
            event = self.db.query(EventDB).filter(EventDB.id == event_id).first()
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            self.db.delete(event)
            self.db.commit()
            
            logger.info(f"Deleted event: {event.title}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting event: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def search_events(self, query: str, params: EventSearchParams) -> Tuple[List[EventResponse], int]:
        """Search events by text query"""
        try:
            # Build search query
            search_filter = or_(
                EventDB.title.ilike(f"%{query}%"),
                EventDB.description.ilike(f"%{query}%"),
                EventDB.location.ilike(f"%{query}%"),
                EventDB.city.ilike(f"%{query}%")
            )
            
            db_query = self.db.query(EventDB).filter(search_filter)
            
            # Apply other filters
            db_query = self._apply_filters(db_query, params)
            
            # Get total count
            total = db_query.count()
            
            # Apply ordering and pagination
            db_query = db_query.order_by(desc(EventDB.date), asc(EventDB.time))
            db_query = db_query.offset(params.offset).limit(params.limit)
            
            events = db_query.all()
            
            return [self._db_to_response(event) for event in events], total
            
        except Exception as e:
            logger.error(f"Error searching events: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_weekend_events(self, params: EventSearchParams) -> Tuple[List[EventResponse], int]:
        """Get events for the upcoming weekend"""
        try:
            # Calculate next weekend dates
            today = datetime.now().date()
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0 and today.weekday() != 4:  # If today is Sunday, next Friday is in 7 days
                days_until_friday = 7
            
            friday = today + timedelta(days=days_until_friday)
            sunday = friday + timedelta(days=2)
            
            # Set datetime boundaries
            friday_start = datetime.combine(friday, datetime.min.time())
            sunday_end = datetime.combine(sunday, datetime.max.time())
            
            # Build query
            db_query = self.db.query(EventDB).filter(
                and_(
                    EventDB.date >= friday_start,
                    EventDB.date <= sunday_end
                )
            )
            
            # Apply other filters
            db_query = self._apply_filters(db_query, params)
            
            # Get total count
            total = db_query.count()
            
            # Apply ordering and pagination
            db_query = db_query.order_by(asc(EventDB.date), asc(EventDB.time))
            db_query = db_query.offset(params.offset).limit(params.limit)
            
            events = db_query.all()
            
            return [self._db_to_response(event) for event in events], total
            
        except Exception as e:
            logger.error(f"Error getting weekend events: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def get_events_by_location(self, params: EventSearchParams, latitude: float, longitude: float, radius_km: float = 10) -> Tuple[List[EventResponse], int]:
        """Get events within a specified radius from a location"""
        try:
            # This is a simplified distance calculation
            # In production, you'd use PostGIS or similar for proper geospatial queries
            
            # For now, we'll get all events and filter by distance
            db_query = self.db.query(EventDB)
            
            # Apply other filters first
            db_query = self._apply_filters(db_query, params)
            
            events = db_query.all()
            
            # Filter by distance
            nearby_events = []
            for event in events:
                if event.latitude and event.longitude:
                    distance = self._calculate_distance(
                        latitude, longitude, 
                        event.latitude, event.longitude
                    )
                    if distance <= radius_km:
                        nearby_events.append(event)
            
            # Sort by distance
            nearby_events.sort(key=lambda e: self._calculate_distance(
                latitude, longitude, e.latitude, e.longitude
            ) if e.latitude and e.longitude else float('inf'))
            
            # Apply pagination
            total = len(nearby_events)
            start = params.offset
            end = start + params.limit
            paginated_events = nearby_events[start:end]
            
            return [self._db_to_response(event) for event in paginated_events], total
            
        except Exception as e:
            logger.error(f"Error getting events by location: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def bulk_create_events(self, events: List[Event]) -> int:
        """Bulk create events (used by crawlers)"""
        try:
            created_count = 0
            
            for event in events:
                # Normalize event
                normalized_event = self.parser.normalize_event(event)
                if not normalized_event:
                    continue
                
                # Check for duplicates
                if self._is_duplicate(normalized_event):
                    continue
                
                # Create database record
                db_event = EventDB(
                    title=normalized_event.title,
                    date=normalized_event.date,
                    time=normalized_event.time,
                    location=normalized_event.location,
                    city=normalized_event.city,
                    latitude=normalized_event.latitude,
                    longitude=normalized_event.longitude,
                    type=normalized_event.type.value if normalized_event.type else None,
                    price=normalized_event.price,
                    description=normalized_event.description,
                    source=normalized_event.source.value,
                    link=normalized_event.link
                )
                
                self.db.add(db_event)
                created_count += 1
            
            self.db.commit()
            logger.info(f"Bulk created {created_count} events")
            return created_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error bulk creating events: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def _apply_filters(self, query, params: EventSearchParams):
        """Apply filters to the query"""
        # City filter
        if params.city:
            query = query.filter(EventDB.city.ilike(f"%{params.city}%"))
        
        # Date range filter
        if params.date_from:
            query = query.filter(EventDB.date >= params.date_from)
        
        if params.date_to:
            query = query.filter(EventDB.date <= params.date_to)
        
        # Event type filter
        if params.type:
            query = query.filter(EventDB.type == params.type.value)
        
        # Location filter
        if params.location:
            query = query.filter(EventDB.location.ilike(f"%{params.location}%"))
        
        # Source filter
        if params.source:
            query = query.filter(EventDB.source == params.source.value)
        
        # Weekend filter
        if params.weekend_only:
            today = datetime.now().date()
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0 and today.weekday() != 4:
                days_until_friday = 7
            
            friday = today + timedelta(days=days_until_friday)
            sunday = friday + timedelta(days=2)
            
            friday_start = datetime.combine(friday, datetime.min.time())
            sunday_end = datetime.combine(sunday, datetime.max.time())
            
            query = query.filter(
                and_(
                    EventDB.date >= friday_start,
                    EventDB.date <= sunday_end
                )
            )
        
        return query

    def _is_duplicate(self, event: Event) -> bool:
        """Check if event is a duplicate"""
        # Check for existing events with same title, date, and location
        existing = self.db.query(EventDB).filter(
            and_(
                EventDB.title.ilike(f"%{event.title}%"),
                EventDB.date == event.date,
                EventDB.location.ilike(f"%{event.location}%")
            )
        ).first()
        
        return existing is not None

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r

    def _db_to_response(self, db_event: EventDB) -> EventResponse:
        """Convert database event to response model"""
        return EventResponse(
            id=db_event.id,
            title=db_event.title,
            date=db_event.date,
            time=db_event.time,
            location=db_event.location,
            city=db_event.city,
            latitude=db_event.latitude,
            longitude=db_event.longitude,
            type=EventType(db_event.type) if db_event.type else None,
            price=db_event.price,
            description=db_event.description,
            source=EventSource(db_event.source),
            link=db_event.link,
            created_at=db_event.created_at
        )
