import re
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple
from difflib import SequenceMatcher
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from app.models.event import Event, EventType, EventSource

logger = logging.getLogger(__name__)


class EventParser:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="bergamo-events-finder")
        
        # Common location variations in Bergamo area
        self.location_normalizations = {
            "bg": "Bergamo",
            "bergamo Alta": "Bergamo",
            "città alta": "Bergamo",
            "bergamo bassa": "Bergamo",
            "albino": "Albino",
            "polaresco": "Polaresco",
            "ponteranica": "Ponteranica",
            "sorisole": "Sorisole",
            "treviso bg": "Trezzo sull'Adda",
            "curno": "Curno",
            "mozzo": "Mozzo",
            "osio sopra": "Osio Sopra",
            "osio sotto": "Osio Sotto"
        }
        
        # Common title patterns to clean
        self.title_clean_patterns = [
            r'^\d+\.\s*',  # Remove numbered prefixes
            r'^\[\w+\]\s*',  # Remove bracketed prefixes
            r'^\w+\s*-\s*',  # Remove source prefixes
            r'\s*-\s*bergamo\s*$',  # Remove location suffixes
            r'\s*-\s*albino\s*$',  # Remove location suffixes
            r'\s*\|\s*.*$',  # Remove everything after |
            r'\s*-\s*.*$',  # Remove everything after -
        ]

    def normalize_events(self, events: List[Event]) -> List[Event]:
        """Normalize and clean a list of events"""
        normalized_events = []
        
        for event in events:
            try:
                normalized_event = self.normalize_event(event)
                if normalized_event:
                    normalized_events.append(normalized_event)
            except Exception as e:
                logger.warning(f"Error normalizing event {event.title}: {e}")
                continue
        
        # Remove duplicates
        deduplicated_events = self.remove_duplicates(normalized_events)
        
        # Add geocoding
        events_with_coords = self.add_geocoding(deduplicated_events)
        
        logger.info(f"Normalized {len(events)} events to {len(events_with_coords)} unique events")
        return events_with_coords

    def normalize_event(self, event: Event) -> Optional[Event]:
        """Normalize a single event"""
        if not event or not event.title:
            return None
        
        # Clean title
        cleaned_title = self.clean_title(event.title)
        if not cleaned_title or len(cleaned_title) < 3:
            return None
        
        # Normalize location and city
        normalized_location = self.normalize_location(event.location)
        normalized_city = self.normalize_city(event.city)
        
        # Normalize date
        normalized_date = self.normalize_date(event.date)
        if not normalized_date:
            return None
        
        # Clean time
        cleaned_time = self.clean_time(event.time)
        
        # Normalize price
        normalized_price = self.normalize_price(event.price)
        
        # Clean description
        cleaned_description = self.clean_description(event.description)
        
        # Validate event type
        validated_type = self.validate_event_type(event.type, cleaned_title, normalized_location)
        
        return Event(
            title=cleaned_title,
            date=normalized_date,
            time=cleaned_time,
            location=normalized_location,
            city=normalized_city,
            latitude=event.latitude,
            longitude=event.longitude,
            type=validated_type,
            price=normalized_price,
            description=cleaned_description,
            source=event.source,
            link=event.link
        )

    def clean_title(self, title: str) -> str:
        """Clean and normalize event title"""
        if not title:
            return ""
        
        title = title.strip()
        
        # Apply cleaning patterns
        for pattern in self.title_clean_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title)
        
        # Capitalize properly
        title = title.title()
        
        return title.strip()

    def normalize_location(self, location: str) -> str:
        """Normalize location name"""
        if not location:
            return "Bergamo"
        
        location = location.strip().lower()
        
        # Apply normalizations
        for variant, standard in self.location_normalizations.items():
            if variant in location:
                return standard
        
        # Capitalize properly
        return location.title()

    def normalize_city(self, city: str) -> str:
        """Normalize city name"""
        if not city:
            return "Bergamo"
        
        city = city.strip().lower()
        
        # Apply normalizations
        for variant, standard in self.location_normalizations.items():
            if variant in city:
                return standard
        
        # Capitalize properly
        return city.title()

    def normalize_date(self, date: datetime) -> Optional[datetime]:
        """Normalize date - ensure it's valid and in the future/past"""
        if not date:
            return None
        
        # If date is too far in the past, it's likely invalid
        if date < datetime.now() - timedelta(days=365):
            return None
        
        # If date is too far in the future, it's likely invalid
        if date > datetime.now() + timedelta(days=365):
            return None
        
        return date

    def clean_time(self, time: Optional[str]) -> Optional[str]:
        """Clean and normalize time"""
        if not time:
            return None
        
        time = time.strip()
        
        # Extract time patterns
        time_patterns = [
            r'(\d{1,2}):(\d{2})',  # 22:00
            r'(\d{1,2})\s*(AM|PM)',  # 10 PM
            r'ore\s+(\d{1,2}):(\d{2})',  # ore 22:00
            r'(\d{1,2})\s*ore',  # 22 ore
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, time, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    if ':' in match.group():  # 22:00 format
                        return f"{match.group(1)}:{match.group(2)}"
                    else:  # 10 PM format
                        hour = int(match.group(1))
                        period = match.group(2).upper()
                        if period == 'PM' and hour != 12:
                            hour += 12
                        elif period == 'AM' and hour == 12:
                            hour = 0
                        return f"{hour:02d}:00"
                elif len(match.groups()) == 3:  # ore 22:00 format
                    return f"{match.group(2)}:{match.group(3)}"
        
        return None

    def normalize_price(self, price: Optional[str]) -> Optional[str]:
        """Normalize price format"""
        if not price:
            return None
        
        price = price.strip().lower()
        
        # Standardize free events
        if any(word in price for word in ['gratis', 'free', 'libero', 'ingresso libero']):
            return "Gratis"
        
        # Extract price numbers
        price_match = re.search(r'(\d+)[,.]?(\d*)', price)
        if price_match:
            whole = price_match.group(1)
            decimal = price_match.group(2) or "00"
            return f"€{whole},{decimal}"
        
        return price.title()

    def clean_description(self, description: Optional[str]) -> Optional[str]:
        """Clean description"""
        if not description:
            return None
        
        description = description.strip()
        
        # Remove HTML tags
        description = re.sub(r'<[^>]+>', '', description)
        
        # Normalize whitespace
        description = re.sub(r'\s+', ' ', description)
        
        # Limit length
        if len(description) > 500:
            description = description[:497] + "..."
        
        return description

    def validate_event_type(self, event_type: Optional[EventType], title: str, location: str) -> EventType:
        """Validate and potentially correct event type"""
        if event_type and event_type != EventType.OTHER:
            return event_type
        
        # Classify based on title and location
        title_lower = title.lower()
        location_lower = location.lower()
        
        # Club venues
        if any(club in location_lower for club in ['edoné', 'ink club', 'druso']):
            if any(keyword in title_lower for keyword in ['live', 'concert', 'band', 'musica']):
                return EventType.LIVE_MUSIC
            else:
                return EventType.CLUB
        
        # Generic classification
        if any(keyword in title_lower for keyword in ['concert', 'live', 'musica', 'band', 'dj']):
            return EventType.LIVE_MUSIC
        elif any(keyword in title_lower for keyword in ['festival', 'sagra', 'festa']):
            return EventType.FESTIVAL
        elif any(keyword in title_lower for keyword in ['teatro', 'spettacolo', 'commedia']):
            return EventType.THEATER
        elif any(keyword in title_lower for keyword in ['mostra', 'esposizione', 'arte']):
            return EventType.EXHIBITION
        elif any(keyword in title_lower for keyword in ['sport', 'calcio', 'partita']):
            return EventType.SPORT
        
        return EventType.OTHER

    def remove_duplicates(self, events: List[Event]) -> List[Event]:
        """Remove duplicate events based on similarity"""
        if not events:
            return []
        
        unique_events = []
        seen_signatures = set()
        
        for event in events:
            signature = self.create_event_signature(event)
            
            # Check for exact signature match
            if signature in seen_signatures:
                continue
            
            # Check for similar events
            is_duplicate = False
            for existing_event in unique_events:
                if self.are_events_similar(event, existing_event):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_events.append(event)
                seen_signatures.add(signature)
        
        return unique_events

    def create_event_signature(self, event: Event) -> str:
        """Create a unique signature for an event"""
        # Normalize title for signature
        title_sig = re.sub(r'[^a-zA-Z0-9]', '', event.title.lower())
        
        # Format date for signature
        date_sig = event.date.strftime('%Y-%m-%d')
        
        # Normalize location for signature
        location_sig = re.sub(r'[^a-zA-Z0-9]', '', event.location.lower())
        
        return f"{title_sig}_{date_sig}_{location_sig}"

    def are_events_similar(self, event1: Event, event2: Event, threshold: float = 0.8) -> bool:
        """Check if two events are similar enough to be considered duplicates"""
        # Same date is required
        if event1.date.date() != event2.date.date():
            return False
        
        # Similar title
        title_similarity = SequenceMatcher(None, event1.title.lower(), event2.title.lower()).ratio()
        if title_similarity < threshold:
            return False
        
        # Similar location (optional but strengthens the match)
        location_similarity = SequenceMatcher(None, event1.location.lower(), event2.location.lower()).ratio()
        
        # Consider them similar if title is very similar OR both title and location are somewhat similar
        return (title_similarity > 0.9) or (title_similarity > threshold and location_similarity > 0.7)

    def add_geocoding(self, events: List[Event]) -> List[Event]:
        """Add latitude and longitude to events"""
        geocoded_events = []
        geocode_cache = {}  # Cache to avoid repeated API calls
        
        for event in events:
            if event.latitude and event.longitude:
                # Event already has coordinates
                geocoded_events.append(event)
                continue
            
            # Create cache key
            cache_key = f"{event.location}, {event.city}"
            
            if cache_key in geocode_cache:
                # Use cached coordinates
                coords = geocode_cache[cache_key]
                event.latitude = coords[0]
                event.longitude = coords[1]
                geocoded_events.append(event)
                continue
            
            # Try to geocode
            try:
                location_query = f"{event.location}, {event.city}, Italy"
                location_data = self.geolocator.geocode(location_query, timeout=5)
                
                if location_data:
                    event.latitude = location_data.latitude
                    event.longitude = location_data.longitude
                    geocode_cache[cache_key] = (location_data.latitude, location_data.longitude)
                    logger.debug(f"Geocoded '{cache_key}' to {event.latitude}, {event.longitude}")
                else:
                    logger.warning(f"Could not geocode '{cache_key}'")
                
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                logger.warning(f"Geocoding failed for '{cache_key}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error geocoding '{cache_key}': {e}")
            
            geocoded_events.append(event)
        
        return geocoded_events

    def filter_weekend_events(self, events: List[Event]) -> List[Event]:
        """Filter events to only include weekend events (Fri-Sun)"""
        weekend_events = []
        
        for event in events:
            if event.date.weekday() >= 4:  # Friday=4, Saturday=5, Sunday=6
                weekend_events.append(event)
        
        return weekend_events

    def filter_by_date_range(self, events: List[Event], date_from: Optional[datetime] = None, 
                           date_to: Optional[datetime] = None) -> List[Event]:
        """Filter events by date range"""
        filtered_events = []
        
        for event in events:
            if date_from and event.date < date_from:
                continue
            if date_to and event.date > date_to:
                continue
            filtered_events.append(event)
        
        return filtered_events
