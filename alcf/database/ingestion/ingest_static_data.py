# Add the project root to Python path to enable absolute imports
import os
import sys
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
import asyncio
import argparse
from datetime import datetime, timezone
from sqlalchemy import delete
from sqlmodel import SQLModel
from alcf.database.models import Facility, Site, Resource, Location, Event, Incident
from alcf.database.database import get_db_session_context, engine


# Data ingestion class
class DataIngestion:
    """Handles data ingestion from JSON files to database models."""
    
    # Class initialization
    def __init__(self):
        
        # Path to where the static data is stored
        data_dir = os.path.join(os.path.dirname(__file__), "static_data")
        
        # Define datetime fields that need parsing
        self.__datetime_fields = ["last_updated", "last_verified"]
        
        # Define default values for required fields that might be missing
        self.__default_values = {
            "resources": {
                "current_status": "unknown",
                "last_verified": None,
                "last_updated": datetime.now(timezone.utc)
            }
        }
        
        # For each static data file ...
        self.__json_data = {}
        for filename in ['facility.json', 'locations.json', 'sites.json', 'resources.json']:
            with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:

                # Load the data and make sure it is a list
                data = json.load(f)
                if isinstance(data, dict):
                    data = [data]

                # Store the data into memory
                self.__json_data[filename] = data
        
    # Parse datetime string
    def __parse_datetime_string(self, dt_string):
        """Parse ISO datetime string to Python datetime object (naive UTC for SQLite compatibility)"""

        # If the datetime string is a string ...
        if isinstance(dt_string, str):

            # Remove 'Z' suffix and parse ISO format (e.g. "2025-07-10T11:28:40.969Z" -> "2025-07-10T11:28:40.969+00:00")
            if dt_string.endswith('Z'):
                dt_string = dt_string[:-1] + '+00:00'

            # Convert the datetime string to a datetime object
            dt = datetime.fromisoformat(dt_string)
            
            # Convert to naive UTC for SQLite compatibility
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            
            return dt

        # If the datetime string is not a string, return it as is
        return dt_string


    # Ingest model into the database
    async def __ingest_model(self, db, filename, db_model_class):
        """Create new database entries or update existing ones based on id field"""
        
        # For each item in the selected json file ...
        for item in self.__json_data[filename]:

            # Parse datetime fields
            for field in self.__datetime_fields:
                if field in item and item[field]:
                    item[field] = self.__parse_datetime_string(item[field])

            # Check if the entry already exists
            existing = await db.get(db_model_class, item['id'])

            # Update entry if already exists
            if existing:
                for key, value in item.items():
                    setattr(existing, key, value)
                
                # Apply default values for missing required fields on existing entries
                model_name = filename.replace('.json', '')
                if model_name in self.__default_values:
                    for field, default_value in self.__default_values[model_name].items():
                        if field not in item or item[field] is None:
                            # Parse the default value if it's a datetime field
                            if field in self.__datetime_fields:
                                default_value = self.__parse_datetime_string(default_value)
                            setattr(existing, field, default_value)

            # Create new entry if does not exist ...
            else:
                # Apply default values for missing required fields
                model_name = filename.replace('.json', '')
                if model_name in self.__default_values:
                    for field, default_value in self.__default_values[model_name].items():
                        if field not in item or item[field] is None:
                            item[field] = default_value
                
                new_entry = db_model_class(**item)
                db.add(new_entry)
        
        # Commit the changes to the database
        await db.commit()


    # Run the complete data ingestion process
    async def run_ingestion(self, db) -> bool:
        """Run the complete data ingestion process."""
        try:
            await self.__ingest_model(db, "facility.json", Facility)
            await self.__ingest_model(db, "locations.json", Location)
            await self.__ingest_model(db, "sites.json", Site)
            await self.__ingest_model(db, "resources.json", Resource)
            
        except Exception as e:
            await db.rollback()
            sys.exit(f"\nError ingesting data: {e}")


    # Clear all data from the database
    async def clear_all_data(self, db) -> bool:
        """Clear all data from the database (useful for testing)."""
        try:
            await db.execute(delete(Resource))
            await db.execute(delete(Site))
            await db.execute(delete(Location))
            await db.execute(delete(Facility))
            await db.execute(delete(Event))
            await db.execute(delete(Incident))
            await db.commit()
        except Exception as e:
            await db.rollback()
            sys.exit(f"\nError clearing data: {e}")


async def main():
    """Main function to run data ingestion."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ingest static data into the facility database')
    parser.add_argument('--clear', action='store_true', 
                       help='Clear all existing data before ingestion')
    args = parser.parse_args()

    # Create tables if not already done
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Get database session using async context manager
    async with get_db_session_context() as db_session:
        try:

            # Create ingestion instance
            ingestion = DataIngestion()

            # Clear database if requested
            if args.clear:
                await ingestion.clear_all_data(db_session)
                print("Database cleared successfully!")

            # Proceed with the data ingestion
            await ingestion.run_ingestion(db_session)
            print("Data ingestion completed successfully!")
                    
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())