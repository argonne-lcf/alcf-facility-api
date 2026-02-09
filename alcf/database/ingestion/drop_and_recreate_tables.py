#!/usr/bin/env python3
"""
Script to drop and recreate only the tables used in static data ingestion.
Use this when you've modified the ingestion models and need to update the database schema.

IMPORTANT: This only affects the tables used in ingestion (Facility, Site, Resource, 
Location, Event, Incident). Other tables in your database will not be touched.
"""
import asyncio
import sys
import os

# Add the project root to Python path
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlmodel import SQLModel
from alcf.database.models import Facility, Site, Resource, Location, Event, Incident
from alcf.database.database import engine

# Define which models/tables should be managed by this script
MANAGED_MODELS = [Facility, Site, Resource, Location, Event, Incident]


async def drop_and_recreate_tables():
    """Drop and recreate only the tables used in static data ingestion."""
    try:
        # Get the table objects for the managed models
        tables_to_manage = [model.__table__ for model in MANAGED_MODELS]
        table_names = [table.name for table in tables_to_manage]
        
        print(f"Managing tables: {', '.join(table_names)}")
        print(f"\nDropping {len(tables_to_manage)} tables...")
        
        async with engine.begin() as conn:
            # Drop only the specified tables
            await conn.run_sync(lambda sync_conn: SQLModel.metadata.drop_all(
                sync_conn, tables=tables_to_manage
            ))
        print(f"{len(tables_to_manage)} tables dropped")
        
        print(f"Creating {len(tables_to_manage)} tables with current schema...")
        async with engine.begin() as conn:
            # Create only the specified tables
            await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(
                sync_conn, tables=tables_to_manage
            ))
        print(f"{len(tables_to_manage)} tables created")
        
        print("\nDatabase schema updated successfully!")
        print("Now run: python alcf/database/ingestion/ingest_static_data.py")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(drop_and_recreate_tables())
