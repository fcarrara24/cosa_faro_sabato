from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.db import get_db, create_tables
from app.services.event_service import EventService
from app.models.event import EventCreate, EventUpdate, EventSearchParams, EventResponse, EventType, EventSource

# Create FastAPI app
app = FastAPI(
    title="Bergamo Events API",
    description="API for finding events in Bergamo area",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()


# Dependency to get event service
def get_event_service(db: Session = Depends(get_db)) -> EventService:
    return EventService(db)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"message": "Bergamo Events API is running", "version": "1.0.0"}


@app.get("/events", response_model=dict, tags=["Events"])
async def get_events(
    city: Optional[str] = Query(None, description="Filter by city"),
    date_from: Optional[datetime] = Query(None, description="Filter events from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter events until this date"),
    type: Optional[EventType] = Query(None, description="Filter by event type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    source: Optional[EventSource] = Query(None, description="Filter by source"),
    weekend_only: bool = Query(False, description="Only weekend events"),
    limit: int = Query(50, ge=1, le=100, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    event_service: EventService = Depends(get_event_service)
):
    """Get events with advanced filtering"""
    params = EventSearchParams(
        city=city,
        date_from=date_from,
        date_to=date_to,
        type=type,
        location=location,
        source=source,
        weekend_only=weekend_only,
        limit=limit,
        offset=offset
    )
    
    events, total = event_service.get_events(params)
    
    return {
        "count": total,
        "events": events,
        "filters": {
            "city": city,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "type": type.value if type else None,
            "location": location,
            "source": source.value if source else None,
            "weekend_only": weekend_only
        }
    }


@app.get("/events/search", response_model=dict, tags=["Events"])
async def search_events(
    q: str = Query(..., description="Search query"),
    city: Optional[str] = Query(None, description="Filter by city"),
    date_from: Optional[datetime] = Query(None, description="Filter events from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter events until this date"),
    type: Optional[EventType] = Query(None, description="Filter by event type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    source: Optional[EventSource] = Query(None, description="Filter by source"),
    weekend_only: bool = Query(False, description="Only weekend events"),
    limit: int = Query(50, ge=1, le=100, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    event_service: EventService = Depends(get_event_service)
):
    """Search events by text query"""
    params = EventSearchParams(
        city=city,
        date_from=date_from,
        date_to=date_to,
        type=type,
        location=location,
        source=source,
        weekend_only=weekend_only,
        limit=limit,
        offset=offset
    )
    
    events, total = event_service.search_events(q, params)
    
    return {
        "count": total,
        "query": q,
        "events": events
    }


@app.get("/events/weekend", response_model=dict, tags=["Events"])
async def get_weekend_events(
    city: Optional[str] = Query(None, description="Filter by city"),
    type: Optional[EventType] = Query(None, description="Filter by event type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    source: Optional[EventSource] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=100, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    event_service: EventService = Depends(get_event_service)
):
    """Get events for the upcoming weekend"""
    params = EventSearchParams(
        city=city,
        type=type,
        location=location,
        source=source,
        limit=limit,
        offset=offset
    )
    
    events, total = event_service.get_weekend_events(params)
    
    return {
        "count": total,
        "events": events,
        "weekend": "upcoming"
    }


@app.get("/events/nearby", response_model=dict, tags=["Events"])
async def get_nearby_events(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"),
    radius_km: float = Query(10, ge=0.1, le=100, description="Search radius in kilometers"),
    city: Optional[str] = Query(None, description="Filter by city"),
    date_from: Optional[datetime] = Query(None, description="Filter events from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter events until this date"),
    type: Optional[EventType] = Query(None, description="Filter by event type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    source: Optional[EventSource] = Query(None, description="Filter by source"),
    weekend_only: bool = Query(False, description="Only weekend events"),
    limit: int = Query(50, ge=1, le=100, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    event_service: EventService = Depends(get_event_service)
):
    """Get events within a specified radius from a location"""
    params = EventSearchParams(
        city=city,
        date_from=date_from,
        date_to=date_to,
        type=type,
        location=location,
        source=source,
        weekend_only=weekend_only,
        limit=limit,
        offset=offset
    )
    
    events, total = event_service.get_events_by_location(params, latitude, longitude, radius_km)
    
    return {
        "count": total,
        "center": {"latitude": latitude, "longitude": longitude},
        "radius_km": radius_km,
        "events": events
    }


@app.get("/events/{event_id}", response_model=EventResponse, tags=["Events"])
async def get_event(event_id: int, event_service: EventService = Depends(get_event_service)):
    """Get a specific event by ID"""
    return event_service.get_event_by_id(event_id)


@app.post("/events", response_model=EventResponse, tags=["Events"])
async def create_event(
    event: EventCreate,
    event_service: EventService = Depends(get_event_service)
):
    """Create a new event"""
    return event_service.create_event(event)


@app.put("/events/{event_id}", response_model=EventResponse, tags=["Events"])
async def update_event(
    event_id: int,
    event: EventUpdate,
    event_service: EventService = Depends(get_event_service)
):
    """Update an existing event"""
    return event_service.update_event(event_id, event)


@app.delete("/events/{event_id}", tags=["Events"])
async def delete_event(event_id: int, event_service: EventService = Depends(get_event_service)):
    """Delete an event"""
    event_service.delete_event(event_id)
    return {"message": "Event deleted successfully"}


@app.get("/stats", response_model=dict, tags=["Statistics"])
async def get_stats(
    event_service: EventService = Depends(get_event_service)
):
    """Get statistics about events"""
    try:
        # Get all events
        events, total = event_service.get_events(EventSearchParams(limit=10000))
        
        # Calculate statistics
        stats = {
            "total_events": total,
            "cities": {},
            "types": {},
            "sources": {},
            "upcoming_events": 0,
            "this_weekend": 0
        }
        
        now = datetime.now()
        
        for event in events:
            # Count by city
            city = event.city
            stats["cities"][city] = stats["cities"].get(city, 0) + 1
            
            # Count by type
            event_type = event.type.value if event.type else "other"
            stats["types"][event_type] = stats["types"].get(event_type, 0) + 1
            
            # Count by source
            source = event.source.value
            stats["sources"][source] = stats["sources"].get(source, 0) + 1
            
            # Count upcoming events
            if event.date > now:
                stats["upcoming_events"] += 1
                
                # Count weekend events
                if event.date.weekday() >= 4:  # Friday, Saturday, Sunday
                    stats["this_weekend"] += 1
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error calculating statistics")


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    try:
        # Check database connection
        from app.database.db import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
