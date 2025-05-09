#!/usr/bin/env python3
"""
API module for the Predicate Relationships Graph.

This module handles fetching data from the OpenFDA API.
"""

import requests
import time
from datetime import datetime
import json
import os
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import pymongo

from src.config import (
    OPENFDA_API_BASE_URL,
    DEFAULT_LIMIT,
    REQUEST_DELAY,
    DATA_DIR,
    PDF_DIR
)
from src import db

def fetch_knumbers(limit: int = DEFAULT_LIMIT, skip: int = 0, api_key: Optional[str] = None, max_retries: int = 3, retry_delay: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Fetch K-numbers from the OpenFDA API.
    
    Args:
        limit: Number of records to fetch per request (max 1000)
        skip: Number of records to skip (for pagination)
        api_key: FDA API key for higher rate limits
        max_retries: Maximum number of retry attempts for failed requests
        retry_delay: Base delay between retries in seconds (increases with each retry)
    
    Returns:
        API response containing device 510(k) data, or None if an error occurred
    """
    logger = logging.getLogger(__name__)
    
    params = {
        'limit': limit,
        'skip': skip,
    }
    
    # Add API key if provided
    if api_key:
        params['api_key'] = api_key
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                # Calculate exponential backoff delay
                current_delay = retry_delay * (2 ** attempt)
                logger.info(f"Retrying request (attempt {attempt+1}/{max_retries}) after {current_delay:.2f}s delay...")
                time.sleep(current_delay)
                
            response = requests.get(OPENFDA_API_BASE_URL, params=params)
            
            # Handle rate limiting (429 Too Many Requests)
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    # Extract retry-after header if available
                    retry_after = response.headers.get('Retry-After')
                    if retry_after and retry_after.isdigit():
                        retry_delay = float(retry_after)
                    
                    logger.warning(f"Rate limited (429). Will retry after {retry_delay}s delay.")
                    continue
                else:
                    logger.error("Rate limit exceeded and max retries reached.")
                    return None
            
            response.raise_for_status()  # Raise an exception for other HTTP errors
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error fetching data: {e}. Retrying...")
            else:
                logger.error(f"Error fetching data after {max_retries} retries: {e}")
                return None
    
    return None

def save_data_to_json(data: Any, filename: str) -> str:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        filename: Name of the file
    
    Returns:
        Path to the saved file
    """
    logger = logging.getLogger(__name__)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Data saved to {filepath}")
    return filepath

def load_data_from_json(filepath: str) -> Any:
    """
    Load data from a JSON file.
    
    Args:
        filepath: Path to the JSON file
    
    Returns:
        Loaded data
    """
    logger = logging.getLogger(__name__)
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading data from {filepath}: {e}")
        return None

def fetch_knumbers_by_date_range(start_date, end_date, api_key=None, limit=1000, skip=0, max_retries=3, retry_delay=2.0):
    """
    Fetch K-numbers from the OpenFDA API by date range
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        api_key (str, optional): FDA API key for higher rate limits
        limit (int, optional): Maximum number of records to fetch per request
        skip (int, optional): Number of records to skip
        max_retries (int, optional): Maximum number of retry attempts
        retry_delay (float, optional): Initial delay between retries in seconds
    
    Returns:
        dict: JSON response from the OpenFDA API
    """
    logger = logging.getLogger(__name__)
    
    # Construct the URL with date range filter
    url = f"https://api.fda.gov/device/510k.json?search=decision_date:[{start_date}+TO+{end_date}]&limit={limit}&skip={skip}"
    
    # Add API key if provided
    if api_key:
        url += f"&api_key={api_key}"
    
    logger.info(f"Fetching records with decision date between {start_date} and {end_date}, skip={skip}, limit={limit}")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                # Calculate exponential backoff delay
                current_delay = retry_delay * (2 ** attempt)
                logger.warning(f"Error fetching data: {str(e)}. Retrying...")
                logger.info(f"Retrying request (attempt {attempt+1}/{max_retries}) after {current_delay:.2f}s delay...")
                time.sleep(current_delay)
            else:
                logger.error(f"Error fetching data after {max_retries} retries: {str(e)}")
                raise
    
    return None

def fetch_all_knumbers_by_date_ranges(api_key=None, date_ranges=None, batch_size=1000, max_failures=5):
    """
    Fetch all K-numbers from the OpenFDA API by iterating through date ranges
    
    Args:
        api_key (str, optional): FDA API key for higher rate limits
        date_ranges (list, optional): List of date range tuples (start_date, end_date)
        batch_size (int, optional): Number of records to fetch per request
        max_failures (int, optional): Maximum consecutive failures to tolerate before stopping
    
    Returns:
        tuple: List of K-numbers, total number of records processed, and MongoDB save results (inserted, updated, skipped)
    """
    logger = logging.getLogger(__name__)
    
    # Default date ranges if none provided (covering from 1976 to current year)
    if not date_ranges:
        current_year = datetime.now().year
        # Create 5-year chunks from 1976 to current year
        date_ranges = []
        start_year = 1976
        while start_year <= current_year:
            end_year = min(start_year + 4, current_year)
            date_ranges.append((f"{start_year}-01-01", f"{end_year}-12-31"))
            start_year = end_year + 1
    
    all_knumbers = []
    consecutive_failures = 0
    total_records = 0
    
    # MongoDB save results
    total_inserted = 0
    total_updated = 0
    total_skipped = 0
    
    # Import db module and establish a single connection upfront
    from src import db
    try:
        mongodb_client = db.get_database_connection()
        mongodb_db = mongodb_client[db.MONGODB_DB]
        mongodb_collection = mongodb_db[db.MONGODB_DEVICES_COLLECTION]
        
        # Create index on k_number if it doesn't exist
        if 'k_number' not in mongodb_collection.index_information():
            mongodb_collection.create_index('k_number', unique=True)
            logger.info(f"Created index on k_number")
        else:
            logger.info(f"Index on k_number already exists")
            
        for start_date, end_date in date_ranges:
            try:
                logger.info(f"Fetching records for date range: {start_date} to {end_date}")
                
                # First make a query to get the total number of records for this date range
                initial_response = fetch_knumbers_by_date_range(
                    start_date=start_date,
                    end_date=end_date, 
                    api_key=api_key,
                    limit=1,
                    skip=0
                )
                
                if not initial_response or 'meta' not in initial_response:
                    logger.warning(f"No results or metadata found for date range {start_date} to {end_date}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logger.error(f"Reached maximum consecutive failures ({max_failures}). Stopping.")
                        break
                    continue
                
                total_for_range = initial_response.get('meta', {}).get('results', {}).get('total', 0)
                logger.info(f"Date range {start_date} to {end_date} has {total_for_range} total records")
                
                # Now fetch all records for this date range using pagination
                range_skip = 0
                while range_skip < total_for_range:
                    try:
                        response = fetch_knumbers_by_date_range(
                            start_date=start_date,
                            end_date=end_date, 
                            api_key=api_key,
                            limit=batch_size,
                            skip=range_skip
                        )
                        
                        if not response or 'results' not in response or not response['results']:
                            logger.warning(f"No results found for date range {start_date} to {end_date} with skip={range_skip}")
                            break
                        
                        # Reset failure count on success
                        consecutive_failures = 0
                        
                        # Process records
                        records = response['results']
                        batch_records = len(records)
                        total_records += batch_records
                        
                        # Extract K-numbers and device info
                        batch_devices_info = []
                        for record in records:
                            k_number = record.get('k_number')
                            if k_number:
                                all_knumbers.append(k_number)
                                
                                # Extract device info with only necessary fields
                                device_info = {
                                    'k_number': k_number,
                                    'device_name': record.get('device_name', ''),
                                    'applicant': record.get('applicant', ''),
                                    'decision_date': record.get('decision_date', ''),
                                    'product_code': record.get('product_code', ''),
                                    'statement_or_summary': record.get('statement_or_summary', ''),
                                    'decision_description': record.get('decision_description', '')
                                }
                                
                                # Add sortable date
                                decision_date = record.get('decision_date', '')
                                if decision_date:
                                    try:
                                        date_obj = datetime.strptime(decision_date, '%Y-%m-%d')
                                        device_info['sortable_date'] = date_obj
                                    except (ValueError, TypeError):
                                        pass
                                
                                batch_devices_info.append(device_info)
                        
                        # Save batch directly to MongoDB using the established connection
                        if batch_devices_info:
                            # Use bulk operations for better performance
                            operations = []
                            for device in batch_devices_info:
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
                                    total_skipped += 1
                            
                            if operations:
                                result = mongodb_collection.bulk_write(operations)
                                inserted = result.upserted_count
                                updated = result.modified_count
                                
                                total_inserted += inserted
                                total_updated += updated
                                
                                logger.info(f"Saved batch to MongoDB: {inserted} inserted, {updated} updated, {total_skipped} skipped")
                        
                        logger.info(f"Processed {batch_records} records from date range {start_date} to {end_date}, skip={range_skip}")
                        
                        # Update the skip value for the next iteration
                        range_skip += batch_records
                        
                        # Add a small delay to be respectful of the API
                        time.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Error processing date range {start_date} to {end_date} with skip={range_skip}: {str(e)}")
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            logger.error(f"Reached maximum consecutive failures ({max_failures}). Stopping.")
                            break
                        # Still try to advance
                        range_skip += batch_size
                        time.sleep(1.0)  # Longer delay after an error
                
                logger.info(f"Completed date range {start_date} to {end_date}, fetched {range_skip} records")
                
            except Exception as e:
                logger.error(f"Error processing date range {start_date} to {end_date}: {str(e)}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    logger.error(f"Reached maximum consecutive failures ({max_failures}). Stopping.")
                    break
    except Exception as e:
        logger.error(f"Error establishing MongoDB connection: {str(e)}")
    
    # Remove duplicates
    all_knumbers = list(set(all_knumbers))
    
    logger.info(f"Total records fetched: {total_records}")
    logger.info(f"Total unique K-numbers: {len(all_knumbers)}")
    logger.info(f"MongoDB results - Inserted: {total_inserted}, Updated: {total_updated}, Skipped: {total_skipped}")
    
    return all_knumbers, total_records, (total_inserted, total_updated, total_skipped)

def fetch_and_save_all_knumbers_by_date_ranges(date_ranges=None, api_key=None, batch_size=1000, max_failures=5):
    """
    Fetch all K-numbers by date ranges and save them to MongoDB and JSON files
    
    Args:
        date_ranges (list, optional): List of date range tuples (start_date, end_date)
        api_key (str, optional): FDA API key for higher rate limits
        batch_size (int, optional): Number of records to fetch per request
        max_failures (int, optional): Maximum consecutive failures to tolerate before stopping
    
    Returns:
        tuple: Path to the knumbers output file, total number of records processed, and MongoDB save results
    """
    logger = logging.getLogger(__name__)
    
    logger.info("Fetching all K-numbers from the OpenFDA API by date ranges")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_knumbers_file = os.path.join(DATA_DIR, f"knumbers_{timestamp}.json")
    
    all_knumbers, total_records, mongodb_results = fetch_all_knumbers_by_date_ranges(
        api_key=api_key,
        date_ranges=date_ranges,
        batch_size=batch_size,
        max_failures=max_failures
    )
    
    # Save all K-numbers to a single file for reference
    logger.info(f"Total unique K-numbers: {len(all_knumbers)}")
    with open(all_knumbers_file, 'w') as f:
        json.dump(all_knumbers, f, indent=2)
    logger.info(f"K-numbers saved to {all_knumbers_file}")
    
    # MongoDB results summary
    total_inserted, total_updated, total_skipped = mongodb_results
    logger.info(f"MongoDB save results - Inserted: {total_inserted}, Updated: {total_updated}, Skipped: {total_skipped}")
    
    return all_knumbers_file, total_records, mongodb_results

def process_batch_files():
    """
    Process existing batch files containing device data and save to MongoDB
    
    Returns:
        tuple: Path to the output knumbers file and MongoDB save results
    """
    logger = logging.getLogger(__name__)
    
    # Find all batch files
    batch_files = []
    for filename in os.listdir(DATA_DIR):
        if filename.startswith("devices_data_batch_") and filename.endswith(".json"):
            batch_files.append(os.path.join(DATA_DIR, filename))
    
    if not batch_files:
        logger.warning("No batch files found to process.")
        return None
    
    logger.info(f"Found {len(batch_files)} batch files to process.")
    
    # Process each batch file
    all_knumbers = []
    total_inserted = 0
    total_updated = 0 
    total_skipped = 0
    
    # Import db module for MongoDB interactions
    from src import db
    
    for batch_file in batch_files:
        logger.info(f"Processing batch file: {batch_file}")
        try:
            with open(batch_file, 'r') as f:
                batch_data = json.load(f)
            
            if isinstance(batch_data, dict) and 'results' in batch_data:
                # Handle format from direct API responses
                records = batch_data['results']
            elif isinstance(batch_data, list):
                # Handle format from previously processed files
                records = batch_data
            else:
                logger.warning(f"Unexpected data format in file: {batch_file}")
                continue
            
            batch_knumbers = []
            batch_devices_info = []
            
            for record in records:
                k_number = record.get('k_number')
                if k_number:
                    batch_knumbers.append(k_number)
                    
                    # Extract device info
                    device_info = {
                        'k_number': k_number,
                        'device_name': record.get('device_name', ''),
                        'applicant': record.get('applicant', ''),
                        'decision_date': record.get('decision_date', ''),
                        'product_code': record.get('product_code', ''),
                        'statement_or_summary': record.get('statement_or_summary', ''),
                        'decision_description': record.get('decision_description', '')
                    }
                    batch_devices_info.append(device_info)
            
            all_knumbers.extend(batch_knumbers)
            
            # Save batch directly to MongoDB
            if batch_devices_info:
                inserted, updated, skipped = db.save_devices_to_mongodb(batch_devices_info)
                total_inserted += inserted
                total_updated += updated
                total_skipped += skipped
                logger.info(f"Saved batch to MongoDB: {inserted} inserted, {updated} updated, {skipped} skipped")
            
            logger.info(f"Processed {len(batch_knumbers)} K-numbers from batch file")
            
        except Exception as e:
            logger.error(f"Error processing batch file {batch_file}: {str(e)}")
    
    # Remove duplicates
    all_knumbers = list(set(all_knumbers))
    
    # Save processed knumbers for reference
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_knumbers_file = os.path.join(DATA_DIR, f"knumbers_{timestamp}.json")
    
    logger.info(f"Total unique K-numbers: {len(all_knumbers)}")
    with open(all_knumbers_file, 'w') as f:
        json.dump(all_knumbers, f, indent=2)
    logger.info(f"K-numbers saved to {all_knumbers_file}")
    
    # MongoDB results summary
    logger.info(f"MongoDB save results - Inserted: {total_inserted}, Updated: {total_updated}, Skipped: {total_skipped}")
    
    return all_knumbers_file, (total_inserted, total_updated, total_skipped) 