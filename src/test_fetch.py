#!/usr/bin/env python3
"""
Test script to check the functionality of fetching and processing K-numbers.
"""

import os
import time
from datetime import datetime

from src.config import logger
from src.api import fetch_knumbers

def test_api_access():
    """Test that we can access the OpenFDA API and get the expected response format."""
    logger.info("Testing API access...")
    
    # Make a simple request to the API
    response = fetch_knumbers(limit=1)
    
    if not response:
        logger.error("Failed to get a response from the API.")
        return False
    
    # Check that the response has the expected structure
    if 'meta' not in response or 'results' not in response:
        logger.error("Response does not have the expected structure.")
        return False
    
    # Check that we can get the total count
    total = response['meta'].get('results', {}).get('total', 0)
    if not total:
        logger.error("Could not determine total count of records.")
        return False
    
    logger.info(f"API access successful. Total records available: {total}")
    return True

def test_pagination():
    """Test that we can paginate through multiple pages of results."""
    logger.info("Testing pagination...")
    
    # Make requests for two consecutive pages
    page1 = fetch_knumbers(limit=10, skip=0)
    if not page1 or 'results' not in page1:
        logger.error("Failed to get first page of results.")
        return False
    
    # Add a small delay to avoid rate limiting
    time.sleep(1)
    
    page2 = fetch_knumbers(limit=10, skip=10)
    if not page2 or 'results' not in page2:
        logger.error("Failed to get second page of results.")
        return False
    
    # Check that we got different results for each page
    page1_knumbers = set([device.get('k_number') for device in page1.get('results', [])])
    page2_knumbers = set([device.get('k_number') for device in page2.get('results', [])])
    
    if not page1_knumbers or not page2_knumbers:
        logger.error("Failed to extract K-numbers from results.")
        return False
    
    # Check for overlap between pages (shouldn't be any)
    overlap = page1_knumbers.intersection(page2_knumbers)
    if overlap:
        logger.warning(f"Found {len(overlap)} overlapping K-numbers between pages. This is unexpected.")
    
    logger.info("Pagination test successful. Able to retrieve different pages of results.")
    return True

def test_large_request():
    """Test that we can request a larger number of records at once."""
    logger.info("Testing large request...")
    
    # Request 100 records at once (well below the 1000 limit)
    response = fetch_knumbers(limit=100)
    
    if not response or 'results' not in response:
        logger.error("Failed to get results for large request.")
        return False
    
    actual_count = len(response.get('results', []))
    if actual_count != 100:
        logger.warning(f"Expected 100 results, but got {actual_count}.")
    
    logger.info(f"Large request test successful. Retrieved {actual_count} records.")
    return True

def main():
    """Run all tests."""
    logger.info("Starting API tests...")
    
    tests = [
        test_api_access,
        test_pagination,
        test_large_request
    ]
    
    success_count = 0
    for test in tests:
        if test():
            success_count += 1
    
    logger.info(f"Completed {success_count}/{len(tests)} tests successfully.")

if __name__ == "__main__":
    main() 