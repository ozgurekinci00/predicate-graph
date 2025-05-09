#!/usr/bin/env python3
"""
Configuration settings for the Predicate Relationships Graph.
"""

import os
import logging
import os.path as path
from dataclasses import dataclass

# API URLs
OPENFDA_API_BASE_URL = "https://api.fda.gov/device/510k.json"
FDA_DATABASE_BASE_URL = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm"

# Directory paths
ROOT_DIR = path.abspath(path.join(path.dirname(__file__), '..'))
DATA_DIR = path.join(ROOT_DIR, 'data')
PDF_DIR = path.join(DATA_DIR, 'pdfs')
LOG_FILE = path.join(DATA_DIR, "app.log")

# API settings
DEFAULT_LIMIT = 1000  # Maximum allowed by the API
REQUEST_DELAY = 0.5  # Delay between API requests in seconds

# Create necessary directories
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# MongoDB settings
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb+srv://admin:xo0kxhpx0123@responder-cluster.olxvljh.mongodb.net/?retryWrites=true&w=majority&appName=responder-cluster")
MONGODB_DB = os.environ.get("MONGODB_DB", "predicate_relationships")
MONGODB_DEVICES_COLLECTION = "devices"

@dataclass
class AppConfig:
    """Application configuration"""
    base_dir: str = ROOT_DIR
    data_dir: str = DATA_DIR
    pdf_dir: str = PDF_DIR
    log_file: str = LOG_FILE
    openfda_api_base_url: str = OPENFDA_API_BASE_URL
    fda_database_base_url: str = FDA_DATABASE_BASE_URL
    default_limit: int = DEFAULT_LIMIT
    request_delay: float = REQUEST_DELAY

# Create a global CONFIG instance
CONFIG = AppConfig()

def setup_logging():
    """Set up logging configuration."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_level = logging.INFO
    
    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = logging.getLogger(__name__) 