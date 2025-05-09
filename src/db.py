#!/usr/bin/env python3
"""
Database operations for the Predicate Relationships Graph.

This module handles connecting to MongoDB and storing/retrieving data.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union
import pymongo
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError

from src.config import DATA_DIR, MONGODB_URI, MONGODB_DB, MONGODB_DEVICES_COLLECTION

# Setup logging
logger = logging.getLogger(__name__)


def get_database_connection() -> MongoClient:
    """
    Get a connection to the MongoDB database
    
    Returns:
        MongoDB client instance
    """
    try:
        client = MongoClient(MONGODB_URI)
        # Test connection
        client.admin.command('ping')
        logger.info(f"Connected to MongoDB at {MONGODB_URI.split('@')[1].split('/?')[0] if '@' in MONGODB_URI else MONGODB_URI}")
        return client
    except PyMongoError as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise


def get_devices_collection():
    """
    Get the devices collection from MongoDB
    
    Returns:
        MongoDB collection for devices
    """
    client = get_database_connection()
    db = client[MONGODB_DB]
    collection = db[MONGODB_DEVICES_COLLECTION]
    return collection


def ensure_indexes():
    """
    Ensure that necessary indexes exist on the devices collection.
    
    This makes queries faster, especially for lookups by k_number.
    """
    logger = logging.getLogger(__name__)
    
    try:
        collection = get_devices_collection()
        
        # Create index on k_number for faster lookups by k_number
        collection.create_index("k_number", unique=True)
        logger.info("Created index on k_number")
        
        # Create index on decision_date for faster date range queries
        collection.create_index("decision_date")
        logger.info("Created index on decision_date")
        
        # Create index on sortable_date for more reliable date sorting
        collection.create_index("sortable_date")
        logger.info("Created index on sortable_date")
        
        # Create index on product_code for filtering by product
        collection.create_index("product_code")
        logger.info("Created index on product_code")
        
        # Create index on predicate_devices for relationship queries
        collection.create_index("predicate_devices")
        logger.info("Created index on predicate_devices")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring indexes: {str(e)}")
        return False


def process_device_for_mongodb(device_data):
    """
    Process device data to extract only necessary fields and add sortable_date.
    
    Args:
        device_data: Raw device data from API
        
    Returns:
        Processed device data with only necessary fields
    """
    # Extract only the fields we want to store
    k_number = device_data.get('k_number')
    if not k_number:
        return None
        
    # Create the processed device with only needed fields
    processed_device = {
        'k_number': k_number,
        'device_name': device_data.get('device_name', ''),
        'applicant': device_data.get('applicant', ''),
        'decision_date': device_data.get('decision_date', ''),
        'product_code': device_data.get('product_code', ''),
        'statement_or_summary': device_data.get('statement_or_summary', ''),
        'decision_description': device_data.get('decision_description', '')
    }
    
    # Add a sortable date field if decision_date exists
    decision_date = device_data.get('decision_date', '')
    if decision_date:
        try:
            # Convert from YYYY-MM-DD to a datetime object
            from datetime import datetime
            date_obj = datetime.strptime(decision_date, '%Y-%m-%d')
            processed_device['sortable_date'] = date_obj
        except (ValueError, TypeError):
            # If date parsing fails, don't add the sortable_date field
            pass
            
    return processed_device


def save_devices_to_mongodb(devices_data):
    """
    Save device information to MongoDB
    
    Args:
        devices_data: List of device information dictionaries
    
    Returns:
        Tuple: (inserted_count, updated_count, skipped_count)
    """
    logger = logging.getLogger(__name__)
    
    if not devices_data:
        logger.warning("No devices to save to MongoDB")
        return (0, 0, 0)
    
    try:
        mongodb_client = get_database_connection()
        db = mongodb_client[MONGODB_DB]
        collection = db[MONGODB_DEVICES_COLLECTION]
        
        # Create index on k_number if it doesn't exist
        if 'k_number' not in collection.index_information():
            collection.create_index('k_number', unique=True)
            logger.info(f"Created index on k_number")
        else:
            logger.info(f"Index on k_number already exists")
        
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        
        # Process and insert device records in bulk
        processed_devices = []
        for device_data in devices_data:
            processed_device = process_device_for_mongodb(device_data)
            if processed_device:
                processed_devices.append(processed_device)
            else:
                skipped_count += 1
                
        if processed_devices:
            # Use bulk operations for better performance
            operations = []
            for device in processed_devices:
                k_number = device.get('k_number')
                if k_number:
                    operations.append(
                        pymongo.UpdateOne(
                            {'k_number': k_number},
                            {'$set': device},
                            upsert=True
                        )
                    )
                else:
                    skipped_count += 1
            
            if operations:
                result = collection.bulk_write(operations)
                inserted_count = result.upserted_count
                updated_count = result.modified_count
                
        logger.info(f"MongoDB update complete: {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped")
        return (inserted_count, updated_count, skipped_count)
    
    except Exception as e:
        logger.error(f"Error saving devices to MongoDB: {str(e)}")
        raise


def get_device_by_knumber(k_number: str) -> Optional[Dict[str, Any]]:
    """
    Get a device by its K-number
    
    Args:
        k_number: The K-number to look up
        
    Returns:
        Device dictionary or None if not found
    """
    collection = get_devices_collection()
    return collection.find_one({"k_number": k_number})


def get_all_knumbers() -> List[str]:
    """
    Get all K-numbers from the database
    
    Returns:
        List of K-numbers
    """
    collection = get_devices_collection()
    return [doc["k_number"] for doc in collection.find({}, {"k_number": 1, "_id": 0})]


def get_devices_count() -> int:
    """
    Get the count of devices in the database
    
    Returns:
        Number of devices
    """
    collection = get_devices_collection()
    return collection.count_documents({})


def test_mongodb_connection() -> Dict[str, Any]:
    """
    Test the MongoDB connection and return diagnostics
    
    Returns:
        Dictionary with connection status and details
    """
    result = {
        "success": False,
        "uri": MONGODB_URI.split('@')[1].split('/?')[0] if '@' in MONGODB_URI else MONGODB_URI,
        "database": MONGODB_DB,
        "collection": MONGODB_DEVICES_COLLECTION,
        "error": None,
        "device_count": 0,
        "database_exists": False,
        "collection_exists": False
    }
    
    try:
        # Get client and test connection
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        result["success"] = True
        
        # Check if database exists
        database_names = client.list_database_names()
        result["database_exists"] = MONGODB_DB in database_names
        
        if result["database_exists"]:
            db = client[MONGODB_DB]
            
            # Check if collection exists
            collection_names = db.list_collection_names()
            result["collection_exists"] = MONGODB_DEVICES_COLLECTION in collection_names
            
            if result["collection_exists"]:
                # Get device count
                result["device_count"] = db[MONGODB_DEVICES_COLLECTION].count_documents({})
        
        return result
    except PyMongoError as e:
        result["success"] = False
        result["error"] = str(e)
        logger.error(f"MongoDB connection test failed: {str(e)}")
        return result


if __name__ == "__main__":
    # Setup logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    
    # Test database connection
    logger.info("Testing MongoDB connection...")
    result = test_mongodb_connection()
    
    if result["success"]:
        logger.info(f"MongoDB connection successful to {result['uri']}")
        logger.info(f"Database: {result['database']}")
        logger.info(f"Collection: {result['collection']}")
        
        if result["database_exists"]:
            logger.info(f"Database exists")
            
            if result["collection_exists"]:
                logger.info(f"Collection exists with {result['device_count']} devices")
            else:
                logger.info(f"Collection does not exist yet")
    else:
        logger.error(f"MongoDB connection failed: {result['error']}") 