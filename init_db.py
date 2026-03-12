#!/usr/bin/env python3
"""
Initialize database tables
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database.db import create_tables, engine
from app.database.schema import EventDB

def main():
    print("Creating database tables...")
    create_tables()
    
    # Verify tables exist
    with engine.connect() as conn:
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = result.fetchall()
        print(f"Tables created: {[table[0] for table in tables]}")
    
    print("Database initialization completed!")

if __name__ == "__main__":
    main()
