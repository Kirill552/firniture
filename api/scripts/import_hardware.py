
import argparse
import json
import logging
from typing import List, Dict, Any
import asyncio

import pandas as pd
from pydantic import ValidationError
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

# Need to configure the path to import from the parent directory
import sys
import os


from api.domain_schemas import HardwareItem as HardwareItemSchema
from api.database import get_db, SessionLocal
from api.models import HardwareItem as HardwareItemModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Loads data from a file (CSV, XLSX, or JSON)."""
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path).to_dict('records')
    elif file_path.endswith(('.xls', '.xlsx')):
        return pd.read_excel(file_path).to_dict('records')
    elif file_path.endswith('.json'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise ValueError("Unsupported file format. Please use CSV, XLSX, or JSON.")

def normalize_and_validate(data: List[Dict[str, Any]]) -> List[HardwareItemSchema]:
    """Normalizes and validates data against the HardwareItem schema."""
    validated_items = []
    for item_data in data:
        try:
            # TODO: Implement a more flexible mapping from source to schema
            item = HardwareItemSchema(**item_data)
            validated_items.append(item)
        except ValidationError as e:
            logger.warning(f"Skipping item due to validation error: {item_data}. Error: {e}")
    return validated_items

async def save_items_to_db(items: List[HardwareItemSchema]):
    """Saves a list of HardwareItem to the database."""
    logger.info(f"Attempting to save {len(items)} items to the database.")
    async with SessionLocal() as db:
        for item_schema in items:
            try:
                # Check if item with SKU already exists
                result = await db.execute(select(HardwareItemModel).filter_by(sku=item_schema.sku))
                existing_item = result.scalars().first()

                item_data = item_schema.model_dump(exclude_unset=True)
                if 'url' in item_data and item_data['url'] is not None:
                    item_data['url'] = str(item_data['url'])

                if existing_item:
                    # Update existing item
                    for key, value in item_data.items():
                        setattr(existing_item, key, value)
                    logger.info(f"Updating item with SKU: {item_schema.sku}")
                else:
                    # Create new item
                    new_item = HardwareItemModel(**item_data)
                    db.add(new_item)
                    logger.info(f"Creating new item with SKU: {item_schema.sku}")

            except IntegrityError as e:
                await db.rollback()
                logger.error(f"Integrity error for SKU {item_schema.sku}: {e}")
            except Exception as e:
                await db.rollback()
                logger.error(f"An unexpected error occurred for SKU {item_schema.sku}: {e}")
        
        await db.commit()
    logger.info("Database saving process finished.")


async def main(file_path: str):
    """Main function to import hardware data."""
    logger.info(f"Starting hardware import from file: {file_path}")
    
    try:
        data = load_data_from_file(file_path)
        logger.info(f"Loaded {len(data)} items from the file.")
        
        validated_items = normalize_and_validate(data)
        logger.info(f"{len(validated_items)} items passed validation.")
        
        if validated_items:
            await save_items_to_db(validated_items)
            logger.info("Hardware import process finished.")
        else:
            logger.warning("No valid items to import.")
            
    except Exception as e:
        logger.error(f"An error occurred during the import process: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import hardware data from a file.")
    parser.add_argument("file_path", type=str, help="The path to the data file (CSV, XLSX, or JSON).")
    
    args = parser.parse_args()
    
    asyncio.run(main(args.file_path))

