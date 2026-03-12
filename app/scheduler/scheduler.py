import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.crawlers.eventbrite import EventbriteCrawler
from app.crawlers.venues import VenueCrawler
from app.services.event_service import EventService

logger = logging.getLogger(__name__)


class EventScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.eventbrite_crawler = EventbriteCrawler()
        self.venue_crawler = VenueCrawler()
        
        # Add jobs
        self._setup_jobs()

    def _setup_jobs(self):
        """Setup scheduled jobs"""
        
        # Crawl Eventbrite every 6 hours
        self.scheduler.add_job(
            func=self.crawl_eventbrite,
            trigger=IntervalTrigger(hours=6),
            id="crawl_eventbrite",
            name="Crawl Eventbrite for events",
            replace_existing=True,
            max_instances=1
        )
        
        # Crawl venues every 8 hours (less frequent as they update less often)
        self.scheduler.add_job(
            func=self.crawl_venues,
            trigger=IntervalTrigger(hours=8),
            id="crawl_venues",
            name="Crawl venue websites for events",
            replace_existing=True,
            max_instances=1
        )
        
        # Cleanup old events daily at 2 AM
        self.scheduler.add_job(
            func=self.cleanup_old_events,
            trigger=CronTrigger(hour=2, minute=0),
            id="cleanup_events",
            name="Cleanup old events",
            replace_existing=True,
            max_instances=1
        )
        
        # Health check every hour
        self.scheduler.add_job(
            func=self.health_check,
            trigger=IntervalTrigger(hours=1),
            id="health_check",
            name="System health check",
            replace_existing=True,
            max_instances=1
        )

    def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("Event scheduler started successfully")
            
            # Run initial crawl
            import asyncio
            asyncio.create_task(self.initial_crawl())
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise

    def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("Event scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")

    async def initial_crawl(self):
        """Run initial crawl when scheduler starts"""
        logger.info("Running initial crawl...")
        try:
            await self.crawl_eventbrite()
            await self.crawl_venues()
            logger.info("Initial crawl completed")
        except Exception as e:
            logger.error(f"Initial crawl failed: {e}")

    async def crawl_eventbrite(self):
        """Crawl Eventbrite for events"""
        logger.info("Starting Eventbrite crawl...")
        start_time = datetime.now()
        
        try:
            # Get events from Eventbrite
            events = await self.eventbrite_crawler.crawl()
            
            if events:
                # Save to database
                db = SessionLocal()
                try:
                    event_service = EventService(db)
                    created_count = event_service.bulk_create_events(events)
                    logger.info(f"Eventbrite crawl completed: {created_count} new events saved")
                finally:
                    db.close()
            else:
                logger.info("Eventbrite crawl completed: no events found")
                
        except Exception as e:
            logger.error(f"Eventbrite crawl failed: {e}")
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Eventbrite crawl took {duration:.2f} seconds")

    async def crawl_venues(self):
        """Crawl venue websites for events"""
        logger.info("Starting venues crawl...")
        start_time = datetime.now()
        
        try:
            # Get events from venues
            events = await self.venue_crawler.crawl_all_venues()
            
            if events:
                # Save to database
                db = SessionLocal()
                try:
                    event_service = EventService(db)
                    created_count = event_service.bulk_create_events(events)
                    logger.info(f"Venues crawl completed: {created_count} new events saved")
                finally:
                    db.close()
            else:
                logger.info("Venues crawl completed: no events found")
                
        except Exception as e:
            logger.error(f"Venues crawl failed: {e}")
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Venues crawl took {duration:.2f} seconds")

    def cleanup_old_events(self):
        """Clean up old events (older than 30 days)"""
        logger.info("Starting cleanup of old events...")
        
        try:
            db = SessionLocal()
            try:
                from datetime import timedelta
                from app.database.schema import EventDB
                
                # Delete events older than 30 days
                cutoff_date = datetime.now() - timedelta(days=30)
                
                deleted_count = db.query(EventDB).filter(
                    EventDB.date < cutoff_date
                ).delete()
                
                db.commit()
                logger.info(f"Cleanup completed: {deleted_count} old events deleted")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def health_check(self):
        """Perform system health check"""
        try:
            db = SessionLocal()
            try:
                # Check database connection
                from app.database.db import engine
                with engine.connect() as conn:
                    conn.execute("SELECT 1")
                
                # Check recent events
                from app.database.schema import EventDB
                recent_events = db.query(EventDB).filter(
                    EventDB.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                ).count()
                
                logger.info(f"Health check passed: {recent_events} events created today")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")

    def get_job_status(self):
        """Get status of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs

    def run_job_now(self, job_id: str):
        """Run a specific job immediately"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"Job {job_id} scheduled to run now")
                return True
            else:
                logger.warning(f"Job {job_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error running job {job_id}: {e}")
            return False


# Global scheduler instance
scheduler = EventScheduler()


def get_scheduler():
    """Get the global scheduler instance"""
    return scheduler
