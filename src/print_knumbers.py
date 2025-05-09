#!/usr/bin/env python3
"""
Utility script to print K-numbers from MongoDB for debugging.
"""

import logging
import re
from src.db import get_devices_collection, get_database_connection

def main():
    """Print sample K-numbers from MongoDB."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Get a sample of devices
    try:
        collection = get_devices_collection()
        sample_size = 20
        
        logger.info(f"Getting a sample of {sample_size} devices from MongoDB...")
        
        # Get documents with explicit k_number field
        devices = list(collection.find({}, {"k_number": 1, "_id": 0}).limit(sample_size))
        
        if not devices:
            logger.error("No devices found in MongoDB")
            return
            
        logger.info(f"Found {len(devices)} devices")
        
        # Check K-number formats
        valid_count = 0
        invalid_count = 0
        
        logger.info("Analyzing K-number formats:")
        for i, device in enumerate(devices):
            k_number = device.get("k_number", "")
            is_valid = bool(re.match(r'^K\d{6}$', k_number))
            status = "Valid" if is_valid else "Invalid"
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                
            logger.info(f"  {i+1}. {k_number} - {status}")
            
        logger.info(f"Summary: {valid_count} valid, {invalid_count} invalid K-numbers")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        
if __name__ == "__main__":
    main() 