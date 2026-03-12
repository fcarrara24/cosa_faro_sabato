#!/usr/bin/env python3
"""
Bergamo Events Finder - Main Application Entry Point

This script starts both the FastAPI server and the event scheduler.
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bergamo_events.log')
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Bergamo Events Finder...")
    
    # Start the scheduler
    from app.scheduler.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduler.start()
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Bergamo Events Finder...")
    scheduler.stop()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    from app.api.main import app
    
    # Add lifespan management
    app.router.lifespan_context = lifespan
    
    return app


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create the FastAPI app
    app = create_app()
    
    # Configuration
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        reload=False,  # Set to True for development
        workers=1  # Use 1 worker since we have an in-memory scheduler
    )
    
    # Start the server
    server = uvicorn.Server(config)
    
    try:
        logger.info("Starting server on http://0.0.0.0:8000")
        server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
