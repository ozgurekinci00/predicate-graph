#!/usr/bin/env python3
"""
Configuration settings for the Predicate Device Analyzer.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Default local MongoDB URI as fallback
DEFAULT_MONGODB_URI = "mongodb://localhost:27017"

# MongoDB configuration
MONGODB_URI = os.environ.get('MONGODB_URI', DEFAULT_MONGODB_URI)
MONGODB_DB = os.environ.get('MONGODB_DB', 'predicate_relationships')
MONGODB_DEVICES_COLLECTION = os.environ.get('MONGODB_DEVICES_COLLECTION', 'devices')

def setup_logging(level=logging.INFO):
    """
    Configure logging for the application.
    
    Args:
        level: The logging level (default: INFO)
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=level, format=log_format)
    
    # Reduce verbose logging from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("PyPDF2").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING) 