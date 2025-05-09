#!/usr/bin/env python3
"""
Predicate Relationships Graph

Main entry point for the predicate device graph application.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

from src import api, db
from src.config import DATA_DIR, setup_logging
from src.pdf_utils import check_pdf_for_knumber, process_knumbers_for_pdfs, test_pdf_retrieval

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Predicate Relationships Graph')
    parser.add_argument('--api-key', type=str, help='FDA API key')
    parser.add_argument('--max-records', type=int, default=None, help='Maximum number of records to fetch for testing')
    parser.add_argument('--batch-size', type=int, default=1000, help='Records per API request')
    parser.add_argument('--fetch-by-date', action='store_true', help='Fetch K-numbers by date ranges')
    parser.add_argument('--process-batches', action='store_true', help='Process existing batch files')
    parser.add_argument('--max-failures', type=int, default=5, help='Maximum consecutive failures to tolerate')
    parser.add_argument('--start-year', type=int, default=1976, help='Start year for date range fetching')
    parser.add_argument('--end-year', type=int, default=None, help='End year for date range fetching')
    parser.add_argument('--year-chunk', type=int, default=1, help='Number of years per chunk for date range fetching')
    parser.add_argument('--mongodb-status', action='store_true', help='Display MongoDB connection status and data info')
    
    # PDF options
    parser.add_argument('--check-pdfs', action='store_true', help='Check for PDF summary documents')
    parser.add_argument('--pdf-test', action='store_true', help='Run PDF retrieval test on sample K-numbers')
    parser.add_argument('--pdf-knumbers', type=str, nargs='+', help='Specific K-numbers to check for PDFs')
    parser.add_argument('--pdf-input-file', type=str, help='JSON file containing K-numbers to check for PDFs')
    parser.add_argument('--pdf-limit', type=int, default=None, help='Limit number of PDFs to check')
    parser.add_argument('--pdf-no-download', action='store_true', help='Check PDF existence without downloading')
    parser.add_argument('--pdf-parse-only', action='store_true', help='Parse PDFs without saving them to disk')
    parser.add_argument('--pdf-output-file', type=str, help='File to save PDF check results')
    parser.add_argument('--pdf-extract-predicates', action='store_true', help='Extract predicate device information from PDFs')
    parser.add_argument('--pdf-save-predicates', type=str, help='File to save extracted predicate relationships')
    
    # Bulk predicate extraction options
    parser.add_argument('--extract-predicates-bulk', action='store_true', help='Extract predicate devices for all devices in the database')
    parser.add_argument('--extract-limit', type=int, default=None, help='Limit the number of devices to process for predicate extraction')
    parser.add_argument('--extract-batch-size', type=int, default=100, help='Number of devices to process in each batch for predicate extraction')
    
    return parser.parse_args()

def main():
    """
    Main application function.
    """
    args = parse_args()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Predicate Relationships Graph")
    logger.info("Initializing...")
    
    if args.pdf_test:
        logger.info("Running PDF retrieval test...")
        results = test_pdf_retrieval()
        logger.info("PDF test completed successfully")
        return
        
    if args.check_pdfs:
        logger.info("Checking for PDF summaries...")
        
        k_numbers = []
        
        # Get K-numbers from specific argument
        if args.pdf_knumbers:
            k_numbers = args.pdf_knumbers
            logger.info(f"Using {len(k_numbers)} K-numbers provided as arguments")
            
        # Get K-numbers from input file
        elif args.pdf_input_file:
            if not os.path.exists(args.pdf_input_file):
                logger.error(f"Input file not found: {args.pdf_input_file}")
                sys.exit(1)
                
            try:
                with open(args.pdf_input_file, 'r') as f:
                    k_numbers = json.load(f)
                logger.info(f"Loaded {len(k_numbers)} K-numbers from {args.pdf_input_file}")
            except Exception as e:
                logger.error(f"Error loading K-numbers from file: {str(e)}")
                sys.exit(1)
        
        # No K-numbers provided
        if not k_numbers:
            logger.error("No K-numbers provided. Use --pdf-knumbers or --pdf-input-file")
            sys.exit(1)
            
        # Apply limit if specified
        if args.pdf_limit and args.pdf_limit < len(k_numbers):
            k_numbers = k_numbers[:args.pdf_limit]
            logger.info(f"Limited to first {args.pdf_limit} K-numbers")
            
        # Process K-numbers
        download = not args.pdf_no_download
        parse_only = args.pdf_parse_only
        extract_predicates = args.pdf_extract_predicates
        
        if parse_only:
            logger.info(f"Checking {len(k_numbers)} K-numbers for PDFs (parse-only mode)")
        else:
            logger.info(f"Checking {len(k_numbers)} K-numbers for PDFs (download={download})")
        
        if extract_predicates:
            logger.info("Extracting predicate device information from PDFs")
        
        results = process_knumbers_for_pdfs(k_numbers, download=download, parse_only=parse_only, extract_predicates=extract_predicates)
        
        # Count PDFs found
        pdfs_found = sum(1 for r in results if r['pdf_exists'])
        logger.info(f"Found PDFs for {pdfs_found}/{len(k_numbers)} K-numbers")
        
        # Count predicate devices found if extraction was enabled
        if extract_predicates:
            predicate_count = sum(len(r.get('predicate_devices', [])) for r in results)
            logger.info(f"Found {predicate_count} predicate device references across all PDFs")
            
            # Create a predicate relationship summary
            if args.pdf_save_predicates:
                # Create a more detailed summary that shows the relationships
                relationships = []
                for r in results:
                    if r['pdf_exists'] and r.get('predicate_devices'):
                        relationships.append({
                            'device': r['k_number'],
                            'predicates': r.get('predicate_devices', [])
                        })
                
                # Save to the specified file
                output_path = args.pdf_save_predicates
                if not os.path.isabs(output_path):
                    output_path = os.path.join(DATA_DIR, output_path)
                    
                with open(output_path, 'w') as f:
                    json.dump(relationships, f, indent=2)
                logger.info(f"Predicate relationships saved to {output_path}")
        
        # Save results if output file specified
        if args.pdf_output_file:
            output_path = args.pdf_output_file
            if not os.path.isabs(output_path):
                output_path = os.path.join(DATA_DIR, output_path)
                
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {output_path}")
            
        return
        
    if args.mongodb_status:
        logger.info("Checking MongoDB status...")
        try:
            # Test connection with detailed diagnostics
            conn_result = db.test_mongodb_connection()
            
            if conn_result["success"]:
                logger.info(f"✓ Successfully connected to MongoDB cluster at {conn_result['uri']}")
                logger.info(f"✓ Database: {conn_result['database']}")
                logger.info(f"✓ Collection: {conn_result['collection']}")
                
                if conn_result["database_exists"]:
                    logger.info(f"✓ Database '{conn_result['database']}' exists")
                    
                    if conn_result["collection_exists"]:
                        logger.info(f"✓ Collection '{conn_result['collection']}' exists")
                        logger.info(f"✓ Total devices: {conn_result['device_count']}")
                        
                        # If devices exist, get a sample
                        if conn_result["device_count"] > 0:
                            collection = db.get_devices_collection()
                            sample_devices = list(collection.find().limit(3))
                            
                            logger.info(f"Sample devices:")
                            for i, device in enumerate(sample_devices):
                                # Remove MongoDB _id field for display
                                if '_id' in device:
                                    del device['_id']
                                logger.info(f"Device {i+1}:")
                                for key, value in device.items():
                                    logger.info(f"  {key}: {value}")
                    else:
                        logger.warning(f"× Collection '{conn_result['collection']}' does not exist yet")
                else:
                    logger.warning(f"× Database '{conn_result['database']}' does not exist yet")
                    
                # Ensure indexes if collection exists
                if conn_result["collection_exists"]:
                    db.ensure_indexes()
            else:
                logger.error(f"× Failed to connect to MongoDB: {conn_result['error']}")
                
            return
        except Exception as e:
            logger.error(f"Error checking MongoDB status: {str(e)}")
            return
        
    if args.max_records:
        logger.info(f"Fetching a sample of {args.max_records} K-numbers for testing")
        
        # Setup date range for sample fetch
        current_year = datetime.now().year
        date_ranges = [(f"{current_year-1}-01-01", f"{current_year}-12-31")]
        
        # Fetch data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        knumbers_file = None
        try:
            knumbers_file, total_records, mongodb_results = api.fetch_and_save_all_knumbers_by_date_ranges(
                date_ranges=date_ranges,
                api_key=args.api_key,
                batch_size=args.max_records,
                max_failures=5
            )
            
            # Log the results
            inserted, updated, skipped = mongodb_results
            logger.info(f"Sample fetch complete: {total_records} records processed")
            logger.info(f"MongoDB results - Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
            
            # Display sample of data for verification
            try:
                # Sample the first few devices
                devices = list(db.get_devices_collection().find().limit(3))
                if devices:
                    logger.info("Sample devices:")
                    for i, device in enumerate(devices, 1):
                        logger.info(f"Device {i}:")
                        for key, value in device.items():
                            if key != '_id':  # Skip the MongoDB ID
                                logger.info(f"  {key}: {value}")
                else:
                    logger.info("No devices found in database")
            except Exception as e:
                logger.error(f"Error sampling devices: {str(e)}")
                
            return
        except Exception as e:
            logger.error(f"Error fetching sample data: {str(e)}")
            return

    if args.fetch_by_date:
        logger.info("Fetching K-numbers by date range")
        
        # Parse the date range parameters
        if args.start_year is None:
            logger.error("Start year is required when using --fetch-by-date")
            return
            
        start_year = args.start_year
        end_year = args.end_year if args.end_year is not None else datetime.now().year
        year_chunk = args.year_chunk
        
        if start_year > end_year:
            logger.error(f"Start year ({start_year}) must be less than or equal to end year ({end_year})")
            return
            
        # Create date ranges in chunks
        date_ranges = []
        for chunk_start in range(start_year, end_year + 1, year_chunk):
            chunk_end = min(chunk_start + year_chunk - 1, end_year)
            date_ranges.append((f"{chunk_start}-01-01", f"{chunk_end}-12-31"))
            
        logger.info(f"Created {len(date_ranges)} date ranges from {start_year} to {end_year} in chunks of {year_chunk} year(s)")
        
        # Fetch data for each date range
        try:
            knumbers_file, total_records, mongodb_results = api.fetch_and_save_all_knumbers_by_date_ranges(
                date_ranges=date_ranges,
                api_key=args.api_key,
                batch_size=args.batch_size,
                max_failures=args.max_failures
            )
            
            # Log the results
            inserted, updated, skipped = mongodb_results
            logger.info(f"Date range fetch complete: {total_records} records processed")
            logger.info(f"MongoDB results - Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
            
            return
        except Exception as e:
            logger.error(f"Error fetching data by date range: {str(e)}")
            return

    if args.process_batches:
        logger.info("Processing existing batch files")
        try:
            result = api.process_batch_files()
            if result:
                knumbers_file, mongodb_results = result
                inserted, updated, skipped = mongodb_results
                logger.info(f"Batch processing complete")
                logger.info(f"MongoDB results - Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
            else:
                logger.warning("No batch files were processed")
            return
        except Exception as e:
            logger.error(f"Error processing batch files: {str(e)}")
            return
    
    if args.extract_predicates_bulk:
        logger.info("Extracting predicate devices for all devices in the database")
        extract_predicates_bulk(limit=args.extract_limit, batch_size=args.extract_batch_size)
        return
    
    logger.info("Completed processing.")

def extract_predicates_bulk(limit: Optional[int] = None, batch_size: int = 100):
    """
    Extract predicate devices for all devices in the database.
    
    Args:
        limit: Maximum number of devices to process (None for all)
        batch_size: Number of devices to process in each batch
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting bulk predicate device extraction (batch_size={batch_size})")
    
    # Check MongoDB connection
    try:
        conn_result = db.test_mongodb_connection()
        if not conn_result["success"] or not conn_result["collection_exists"]:
            logger.error("MongoDB connection failed or collection does not exist")
            return
        
        logger.info(f"Connected to MongoDB, found {conn_result['device_count']} devices")
        
        # Get the device collection
        collection = db.get_devices_collection()
        
        # Get all devices with K-numbers starting with 'K'
        query = {"k_number": {"$regex": "^K"}}
        projection = {"_id": 1, "k_number": 1}
        
        # Apply limit if specified
        cursor = collection.find(query, projection)
        if limit:
            cursor = cursor.limit(limit)
            logger.info(f"Limited to processing {limit} devices")
        
        # Convert cursor to list to get count
        devices = list(cursor)
        total_devices = len(devices)
        logger.info(f"Found {total_devices} devices with K-numbers to process")
        
        # Process devices in batches
        processed_count = 0
        pdf_found_count = 0
        predicates_found_count = 0
        device_with_predicates_count = 0
        
        # Process in batches to avoid memory issues
        for i in range(0, total_devices, batch_size):
            batch = devices[i:i+batch_size]
            
            # Log what we're working with
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_devices-1)//batch_size + 1} ({len(batch)} devices)")
            
            # Show a sample of the raw batch data for debugging
            if len(batch) > 0:
                sample_device = batch[0]
                logger.info(f"Sample device from batch: {sample_device}")
                
            # More detailed logging about the batch
            k_numbers_in_batch = [str(device.get("k_number", "N/A")) for device in batch]
            logger.info(f"K-numbers in batch: {', '.join(k_numbers_in_batch[:5])}" + 
                        (f" (and {len(k_numbers_in_batch) - 5} more)" if len(k_numbers_in_batch) > 5 else ""))
            
            # Filter out irregular K-numbers
            valid_k_numbers = []
            skipped_irregular_count = 0
            irregular_examples = []
            for device in batch:
                k_number = device.get("k_number", "")
                # Validate K-number format (K followed by 6 digits)
                if re.match(r'^K\d{6}$', k_number):
                    valid_k_numbers.append(k_number)
                else:
                    skipped_irregular_count += 1
                    # Keep track of examples for logging
                    if len(irregular_examples) < 5:  # Limit to 5 examples
                        irregular_examples.append(k_number)
                    logger.debug(f"Skipping irregular K-number format: {k_number}")
            
            if skipped_irregular_count > 0:
                logger.info(f"Skipped {skipped_irregular_count} devices with irregular K-numbers. Examples: {', '.join(irregular_examples)}")
                
            # Check if we have any valid K-numbers to process
            if not valid_k_numbers:
                logger.warning(f"No valid K-numbers in this batch, skipping")
                processed_count += len(batch)
                continue
                
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_devices-1)//batch_size + 1} ({len(valid_k_numbers)} valid devices)")
            
            # Check for PDFs and extract predicates
            results = process_knumbers_for_pdfs(valid_k_numbers, download=False, parse_only=True, extract_predicates=True)
            
            # Update MongoDB records with predicate information
            for result in results:
                k_number = result["k_number"]
                predicate_devices = result.get("predicate_devices", [])
                
                # Update counters
                processed_count += 1
                if result["pdf_exists"]:
                    pdf_found_count += 1
                
                if predicate_devices:
                    device_with_predicates_count += 1
                    predicates_found_count += len(predicate_devices)
                    
                    # Update the MongoDB document with predicate devices
                    update_result = collection.update_one(
                        {"k_number": k_number},
                        {"$set": {"predicate_devices": predicate_devices}}
                    )
                    
                    if update_result.modified_count > 0:
                        logger.debug(f"Updated {k_number} with {len(predicate_devices)} predicate devices")
            
            # Log progress
            if (i + batch_size) % (batch_size * 10) == 0 or (i + batch_size) >= total_devices:
                logger.info(f"Progress: {processed_count}/{total_devices} devices processed")
                logger.info(f"Found PDFs for {pdf_found_count} devices")
                logger.info(f"Found {predicates_found_count} predicate references across {device_with_predicates_count} devices")
                
        # Log final statistics
        logger.info("Bulk predicate extraction completed")
        logger.info(f"Processed {processed_count}/{total_devices} devices")
        logger.info(f"Found PDFs for {pdf_found_count} devices ({pdf_found_count/processed_count*100:.1f}%)")
        logger.info(f"Found {predicates_found_count} predicate references across {device_with_predicates_count} devices")
        logger.info(f"Average predicates per device with predicates: {predicates_found_count/max(1, device_with_predicates_count):.1f}")
        
    except Exception as e:
        logger.error(f"Error in bulk predicate extraction: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 