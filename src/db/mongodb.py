#!/usr/bin/env python3
"""
MongoDB operations for the Predicate Relationships Graph.

This module handles connecting to MongoDB and storing/retrieving data.
"""

import logging
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from src.utils.config import MONGODB_URI, MONGODB_DB, MONGODB_DEVICES_COLLECTION

# Setup logging
logger = logging.getLogger(__name__)

# Global connection instance for connection pooling
_mongo_client = None
_db = None
_devices_collection = None
_is_initialized = False

def initialize_db_connection():
    """
    Initialize the MongoDB connection and collections once
    to enable connection pooling.
    
    Returns:
        bool: True if connection was successful, False otherwise
    """
    global _mongo_client, _db, _devices_collection, _is_initialized
    
    if _is_initialized:
        return True
    
    try:
        _mongo_client = MongoClient(MONGODB_URI, maxPoolSize=10)
        # Test connection
        _mongo_client.admin.command('ping')
        _db = _mongo_client[MONGODB_DB]
        _devices_collection = _db[MONGODB_DEVICES_COLLECTION]
        
        # Ensure index on k_number exists
        if 'k_number_1' not in _devices_collection.index_information():
            _devices_collection.create_index("k_number", unique=True)
            logger.info("Created index on k_number field")
        
        logger.info(f"Connected to MongoDB at {MONGODB_URI.split('@')[1].split('/?')[0] if '@' in MONGODB_URI else MONGODB_URI}")
        _is_initialized = True
        return True
    except PyMongoError as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        _is_initialized = False
        return False

# Initialize connection at module load time
initialize_db_connection()

def get_database_connection() -> MongoClient:
    """
    Get a connection to the MongoDB database
    
    Returns:
        MongoDB client instance
    """
    global _mongo_client
    
    if not _is_initialized:
        initialize_db_connection()
    
    return _mongo_client


def get_devices_collection():
    """
    Get the devices collection from MongoDB
    
    Returns:
        MongoDB collection for devices
    """
    global _devices_collection
    
    if not _is_initialized:
        initialize_db_connection()
    
    return _devices_collection


def save_device_to_mongodb(device_data: Dict[str, Any]) -> bool:
    """
    Save a single device document to MongoDB
    
    Args:
        device_data: Device information dictionary including k_number and optional predicate_devices list
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not device_data or 'k_number' not in device_data:
        logger.warning("Invalid device data: missing k_number")
        return False
    
    if not _is_initialized and not initialize_db_connection():
        logger.error("Cannot save device: MongoDB connection not available")
        return False
    
    try:
        collection = get_devices_collection()
        
        # Create a copy to avoid modifying the original
        device_to_save = device_data.copy()
        
        # Upsert the document (update if exists, insert if not)
        result = collection.update_one(
            {'k_number': device_to_save['k_number']},
            {'$set': device_to_save},
            upsert=True
        )
        
        if result.upserted_id:
            logger.info(f"Inserted device {device_to_save['k_number']} into MongoDB")
        else:
            logger.info(f"Updated device {device_to_save['k_number']} in MongoDB")
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving device {device_data.get('k_number')} to MongoDB: {str(e)}")
        return False


def get_device_by_knumber(k_number: str) -> Optional[Dict[str, Any]]:
    """
    Get a device by its K-number
    
    Args:
        k_number: The K-number to look up
        
    Returns:
        Device dictionary or None if not found
    """
    if not _is_initialized and not initialize_db_connection():
        logger.error("Cannot get device: MongoDB connection not available")
        return None
        
    collection = get_devices_collection()
    return collection.find_one({"k_number": k_number})


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
    
    # Use existing connection if available
    global _mongo_client, _is_initialized
    
    try:
        client = _mongo_client if _is_initialized else MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        
        # Only ping if using a new connection
        if not _is_initialized:
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