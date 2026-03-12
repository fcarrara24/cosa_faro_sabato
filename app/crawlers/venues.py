import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin
import re
import logging
from playwright.async_api import async_playwright

from app.models.event import Event, EventSource, EventType

logger = logging.getLogger(__name__)


class VenueCrawler:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        
        self.venues = {
            "edoné": {
                "url": "https://www.edoneclub.it/",
                "city": "Bergamo",
                "location": "Edoné",
                "base_url": "https://www.edoneclub.it"
            },
            "druso": {
                "url": "https://www.druso.it/",
                "city": "Bergamo", 
                "location": "Druso",
                "base_url": "https://www.druso.it"
            },
            "ink_club": {
                "url": "https://www.inkclubbergamo.it/",
                "city": "Bergamo",
                "location": "Ink Club", 
                "base_url": "https://www.inkclubbergamo.it"
            },
            "polaresco": {
                "url": "https://www.polaresco.it/",
                "city": "Polaresco",
                "location": "Polaresco",
                "base_url": "https://www.polaresco.it"
            }
        }

    async def crawl_all_venues(self) -> List[Event]:
        """Crawl all configured venues"""
        all_events = []
        
        for venue_name, venue_config in self.venues.items():
            try:
                logger.info(f"Crawling venue: {venue_name}")
                events = await self._crawl_venue(venue_name, venue_config)
                all_events.extend(events)
                logger.info(f"Found {len(events)} events at {venue_name}")
            except Exception as e:
                logger.error(f"Error crawling {venue_name}: {e}")
                continue
                
        return all_events

    async def _crawl_venue(self, venue_name: str, venue_config: dict) -> List[Event]:
        """Crawl a specific venue"""
        try:
            # Try with httpx first (faster)
            events = await self._crawl_with_httpx(venue_name, venue_config)
            
            # If no events found, try with Playwright for JS-heavy sites
            if not events:
                logger.info(f"No events found with httpx for {venue_name}, trying Playwright")
                events = await self._crawl_with_playwright(venue_name, venue_config)
                
            return events
            
        except Exception as e:
            logger.error(f"Error crawling {venue_name}: {e}")
            return []

    async def _crawl_with_httpx(self, venue_name: str, venue_config: dict) -> List[Event]:
        """Crawl venue using httpx (for static sites)"""
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                response = await client.get(venue_config["url"])
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                return self._extract_events_from_soup(soup, venue_name, venue_config)
                
        except Exception as e:
            logger.warning(f"HTTPX crawling failed for {venue_name}: {e}")
            return []

    async def _crawl_with_playwright(self, venue_name: str, venue_config: dict) -> List[Event]:
        """Crawl venue using Playwright (for dynamic sites)"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto(venue_config["url"], wait_until="networkidle")
                await page.wait_for_timeout(2000)  # Wait for dynamic content
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                events = self._extract_events_from_soup(soup, venue_name, venue_config)
                
                await browser.close()
                return events
                
        except Exception as e:
            logger.warning(f"Playwright crawling failed for {venue_name}: {e}")
            return []

    def _extract_events_from_soup(self, soup: BeautifulSoup, venue_name: str, venue_config: dict) -> List[Event]:
        """Extract events from BeautifulSoup object"""
        events = []
        
        # Common selectors for event listings
        event_selectors = [
            '[class*="event"]',
            '[class*="concert"]', 
            '[class*="show"]',
            '[class*="programma"]',
            '[class*="calendario"]',
            'article',
            '.post',
            '.entry'
        ]
        
        event_elements = []
        for selector in event_selectors:
            elements = soup.select(selector)
            if elements:
                event_elements = elements
                break
        
        # Also look for date patterns in the entire page
        if not event_elements:
            event_elements = self._find_elements_with_dates(soup)
        
        for element in event_elements[:20]:  # Limit to avoid processing too many elements
            try:
                event = self._extract_venue_event(element, venue_name, venue_config)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning(f"Error extracting event from element: {e}")
                continue
        
        return events

    def _find_elements_with_dates(self, soup: BeautifulSoup) -> List:
        """Find elements that contain date patterns"""
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4}',
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}'
        ]
        
        elements_with_dates = []
        for pattern in date_patterns:
            elements = soup.find_all(text=re.compile(pattern, re.IGNORECASE))
            for element in elements:
                parent = element.parent
                if parent and parent not in elements_with_dates:
                    elements_with_dates.append(parent)
        
        return elements_with_dates

    def _extract_venue_event(self, element, venue_name: str, venue_config: dict) -> Optional[Event]:
        """Extract event data from a venue element"""
        try:
            # Extract title
            title = self._extract_title(element)
            if not title or len(title) < 3:
                return None

            # Extract date
            event_date = self._extract_date(element)
            if not event_date:
                return None

            # Extract time
            time = self._extract_time(element)

            # Extract price
            price = self._extract_price(element)

            # Extract description
            description = self._extract_description(element)

            # Extract link
            link = self._extract_link(element, venue_config["base_url"])

            # Classify event type
            event_type = self._classify_venue_event_type(title, venue_name)

            return Event(
                title=title,
                date=event_date,
                time=time,
                location=venue_config["location"],
                city=venue_config["city"],
                source=EventSource.VENUE_WEBSITE,
                link=link,
                type=event_type,
                price=price,
                description=description
            )

        except Exception as e:
            logger.warning(f"Error extracting venue event: {e}")
            return None

    def _extract_title(self, element) -> Optional[str]:
        """Extract title from element"""
        # Try different selectors for title
        title_selectors = [
            'h1', 'h2', 'h3', 'h4',
            '[class*="title"]',
            '[class*="name"]',
            'a[href]',
            'strong',
            'b'
        ]
        
        for selector in title_selectors:
            title_elem = element.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 3:
                    return title
        
        # Fallback to element text
        text = element.get_text(strip=True)
        if text and len(text) < 200:  # Likely a title if short
            return text
            
        return None

    def _extract_date(self, element) -> Optional[datetime]:
        """Extract date from element"""
        text = element.get_text()
        
        # Try to find date in the element text
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})',
            r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})'
        ]
        
        month_map = {
            'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
            'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
            'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if '/' in match.group():  # Numeric format
                            day, month, year = groups
                            return datetime(int(year), int(month), int(day))
                        else:  # Text format
                            day, month, year = groups
                            month_num = month_map.get(month.lower(), 1)
                            return datetime(int(year), int(month_num), int(day))
                except:
                    continue
        
        # Look for relative dates
        if any(word in text.lower() for word in ['oggi', 'today']):
            return datetime.now()
        elif any(word in text.lower() for word in ['domani', 'tomorrow']):
            return datetime.now() + timedelta(days=1)
        elif any(word in text.lower() for word in ['stasera', 'tonight']):
            return datetime.now().replace(hour=22, minute=0)
        
        return None

    def _extract_time(self, element) -> Optional[str]:
        """Extract time from element"""
        text = element.get_text()
        
        time_patterns = [
            r'(\d{1,2}):(\d{2})',
            r'(\d{1,2})\s*(AM|PM)',
            r'ore\s+(\d{1,2}):(\d{2})',
            r'(\d{1,2})\s*ore'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
                
        return None

    def _extract_price(self, element) -> Optional[str]:
        """Extract price from element"""
        text = element.get_text()
        
        # Look for price patterns
        price_patterns = [
            r'€\s*\d+',
            r'\d+\s*€',
            r'€\s*\d+,\d+',
            r'\d+,\d+\s*€',
            r'gratis',
            r'free',
            r'ingresso\s*libero'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
                
        return None

    def _extract_description(self, element) -> Optional[str]:
        """Extract description from element"""
        # Try to find description in p tags or divs with description classes
        desc_selectors = [
            '[class*="description"]',
            '[class*="desc"]',
            'p',
            '.content'
        ]
        
        for selector in desc_selectors:
            desc_elem = element.select_one(selector)
            if desc_elem:
                desc = desc_elem.get_text(strip=True)
                if desc and len(desc) > 20:  # Reasonable description length
                    return desc[:500]  # Limit length
        
        return None

    def _extract_link(self, element, base_url: str) -> str:
        """Extract link from element"""
        link_elem = element.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('http'):
                return href
            else:
                return urljoin(base_url, href)
        
        # Fallback to venue URL
        return base_url

    def _classify_venue_event_type(self, title: str, venue_name: str) -> EventType:
        """Classify event type based on title and venue"""
        title_lower = title.lower()
        
        # Venue-specific classifications
        if venue_name in ['edoné', 'ink_club']:
            # These are primarily clubs
            if any(keyword in title_lower for keyword in ['live', 'concert', 'band']):
                return EventType.LIVE_MUSIC
            else:
                return EventType.CLUB
        elif venue_name == 'druso':
            # Druso has more varied programming
            if any(keyword in title_lower for keyword in ['teatro', 'spettacolo']):
                return EventType.THEATER
            elif any(keyword in title_lower for keyword in ['concert', 'live', 'musica']):
                return EventType.LIVE_MUSIC
            else:
                return EventType.OTHER
        else:
            # Generic classification
            if any(keyword in title_lower for keyword in ['concert', 'live', 'musica', 'band']):
                return EventType.LIVE_MUSIC
            elif any(keyword in title_lower for keyword in ['festival', 'sagra']):
                return EventType.FESTIVAL
            elif any(keyword in title_lower for keyword in ['teatro', 'spettacolo']):
                return EventType.THEATER
            else:
                return EventType.OTHER
