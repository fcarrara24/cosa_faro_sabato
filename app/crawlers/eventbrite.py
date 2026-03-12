import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin, quote
import re
import logging

from app.models.event import Event, EventSource, EventType

logger = logging.getLogger(__name__)


class EventbriteCrawler:
    def __init__(self):
        self.base_url = "https://www.eventbrite.com"
        self.bergamo_url = "https://www.eventbrite.com/d/italy--bergamo/events/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

    async def crawl(self) -> List[Event]:
        """Crawl Eventbrite for events in Bergamo area"""
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                response = await client.get(self.bergamo_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                events = []
                
                # Look for event cards - Eventbrite uses different selectors
                event_cards = soup.find_all(['div', 'article'], class_=re.compile(r'event|card|listing'))
                
                for card in event_cards:
                    try:
                        event = self._extract_event_from_card(card)
                        if event:
                            events.append(event)
                    except Exception as e:
                        logger.warning(f"Error extracting event from card: {e}")
                        continue
                
                logger.info(f"Found {len(events)} events from Eventbrite")
                return events
                
        except Exception as e:
            logger.error(f"Error crawling Eventbrite: {e}")
            return []

    def _extract_event_from_card(self, card) -> Optional[Event]:
        """Extract event data from a card element"""
        try:
            # Extract title
            title_elem = card.find(['h1', 'h2', 'h3', 'span'], class_=re.compile(r'title|name'))
            if not title_elem:
                title_elem = card.find('a', href=re.compile(r'eid='))
            
            if not title_elem:
                return None
                
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 3:
                return None

            # Extract link
            link_elem = card.find('a', href=True)
            if not link_elem:
                return None
                
            link = urljoin(self.base_url, link_elem['href'])

            # Extract date and time
            date_elem = card.find(['time', 'span', 'div'], class_=re.compile(r'date|time|when'))
            date_text = ""
            if date_elem:
                date_text = date_elem.get_text(strip=True)
            
            # Try to extract from datetime attribute
            datetime_attr = date_elem.get('datetime') if date_elem else None
            if datetime_attr:
                event_date = self._parse_datetime(datetime_attr)
            else:
                event_date = self._parse_date_text(date_text)

            if not event_date:
                return None

            # Extract location
            location_elem = card.find(['span', 'div', 'p'], class_=re.compile(r'location|venue|place'))
            location = location_elem.get_text(strip=True) if location_elem else "Bergamo"

            # Extract price
            price_elem = card.find(['span', 'div'], class_=re.compile(r'price|cost|ticket'))
            price = price_elem.get_text(strip=True) if price_elem else None

            # Determine event type
            event_type = self._classify_event_type(title, location)

            return Event(
                title=title,
                date=event_date,
                time=self._extract_time(date_text),
                location=location,
                city="Bergamo",
                source=EventSource.EVENTBRITE,
                link=link,
                type=event_type,
                price=price
            )

        except Exception as e:
            logger.warning(f"Error extracting event: {e}")
            return None

    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse ISO datetime string"""
        try:
            # Handle Eventbrite's datetime format
            if 'T' in datetime_str:
                return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            else:
                return datetime.strptime(datetime_str, '%Y-%m-%d')
        except:
            return None

    def _parse_date_text(self, date_text: str) -> Optional[datetime]:
        """Parse date from text"""
        if not date_text:
            return None
            
        try:
            # Common Italian date patterns
            patterns = [
                r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # "14 Marzo 2026"
                r'(\w+)\s+(\d{1,2}),\s+(\d{4})',  # "Mar 14, 2026"
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # "14/03/2026"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, date_text)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        if pattern == patterns[0]:  # Italian format
                            day, month, year = groups
                            month_map = {
                                'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
                                'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
                                'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
                            }
                            month_num = month_map.get(month.lower(), month)
                            return datetime(int(year), int(month_num), int(day))
                        elif pattern == patterns[1]:  # English format
                            month, day, year = groups
                            month_map = {
                                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                            }
                            month_num = month_map.get(month.lower()[:3], month)
                            return datetime(int(year), int(month_num), int(day))
                        else:  # Numeric format
                            day, month, year = groups
                            return datetime(int(year), int(month), int(day))
            
            # If no pattern matches, try to parse relative dates
            if any(word in date_text.lower() for word in ['oggi', 'today']):
                return datetime.now()
            elif any(word in date_text.lower() for word in ['domani', 'tomorrow']):
                return datetime.now() + timedelta(days=1)
            elif any(word in date_text.lower() for word in ['stasera', 'tonight']):
                return datetime.now().replace(hour=22, minute=0)
                
        except Exception as e:
            logger.warning(f"Error parsing date '{date_text}': {e}")
            
        return None

    def _extract_time(self, date_text: str) -> Optional[str]:
        """Extract time from date text"""
        if not date_text:
            return None
            
        # Look for time patterns like "22:00", "10 PM", "ore 22"
        time_patterns = [
            r'(\d{1,2}):(\d{2})',  # "22:00"
            r'(\d{1,2})\s*(AM|PM)',  # "10 PM"
            r'ore\s+(\d{1,2}):(\d{2})',  # "ore 22:00"
            r'(\d{1,2})\s*ore',  # "22 ore"
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, date_text, re.IGNORECASE)
            if match:
                return match.group(0)
                
        return None

    def _classify_event_type(self, title: str, location: str) -> EventType:
        """Classify event type based on title and location"""
        title_lower = title.lower()
        location_lower = location.lower()
        
        # Keywords for different event types
        if any(keyword in title_lower for keyword in ['concert', 'live', 'musica', 'band', 'dj set']):
            return EventType.LIVE_MUSIC
        elif any(keyword in title_lower for keyword in ['club', 'serata', 'party', 'festa']):
            return EventType.CLUB
        elif any(keyword in title_lower for keyword in ['festival', 'sagra', 'festa patronale']):
            return EventType.FESTIVAL
        elif any(keyword in title_lower for keyword in ['teatro', 'spettacolo', 'commedia']):
            return EventType.THEATER
        elif any(keyword in title_lower for keyword in ['mostra', 'esposizione', 'arte']):
            return EventType.EXHIBITION
        elif any(keyword in title_lower for keyword in ['sport', 'calcio', 'partita', 'gara']):
            return EventType.SPORT
        else:
            return EventType.OTHER
