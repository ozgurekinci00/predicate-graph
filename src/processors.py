#!/usr/bin/env python3
"""
Data processing module for the Predicate Relationships Graph.

This module handles processing and extracting information from FDA data.
"""

import re
import logging
from typing import Dict, List, Any, Optional

def normalize_knumber(k_number: str) -> Optional[str]:
    """
    Normalize K-number format (e.g., K864052, K864052.000, etc. to K864052)
    
    Args:
        k_number: K-number to normalize
    
    Returns:
        Normalized K-number or None if invalid
    """
    if not k_number:
        return None
        
    # Remove any trailing decimal part (e.g., .000)
    k_number = re.sub(r'\..*$', '', k_number)
    
    # Ensure it starts with 'K'
    if not k_number.upper().startswith('K'):
        k_number = 'K' + k_number
    
    # Ensure consistent case (uppercase 'K')
    k_number = 'K' + k_number[1:]
    
    return k_number

def extract_device_info(devices_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extract essential device information including K-numbers.
    
    Args:
        devices_data: List of device data dictionaries from the API
    
    Returns:
        List of dictionaries with essential device information
    """
    devices_info = []
    
    for device in devices_data:
        if 'k_number' in device:
            device_info = {
                'k_number': normalize_knumber(device['k_number']),
                'device_name': device.get('device_name', ''),
                'applicant': device.get('applicant', ''),
                'decision_date': device.get('decision_date', ''),
                'product_code': device.get('product_code', ''),
                'statement_or_summary': device.get('statement_or_summary', ''),
                'decision_description': device.get('decision_description', ''),
            }
            devices_info.append(device_info)
    
    return devices_info

def extract_knumbers_only(devices_data: List[Dict[str, Any]]) -> List[str]:
    """
    Extract only the K-numbers from the devices data.
    
    Args:
        devices_data: List of device data dictionaries from the API
    
    Returns:
        List of normalized K-numbers
    """
    knumbers = []
    
    for device in devices_data:
        if 'k_number' in device:
            knumber = normalize_knumber(device['k_number'])
            if knumber:
                knumbers.append(knumber)
    
    return knumbers

def process_batched_data(batch_files: List[str]) -> Dict[str, Any]:
    """
    Process multiple batches of data and combine results.
    
    Args:
        batch_files: List of file paths to batched data
    
    Returns:
        Dictionary with combined results
    """
    from src.api import load_data_from_json
    
    all_knumbers = []
    all_devices_info = []
    
    for file_path in batch_files:
        logger.info(f"Processing batch file: {file_path}")
        batch_data = load_data_from_json(file_path)
        
        if not batch_data:
            logger.warning(f"Failed to load data from {file_path}")
            continue
        
        # Extract K-numbers and device info
        knumbers = extract_knumbers_only(batch_data)
        devices_info = extract_device_info(batch_data)
        
        all_knumbers.extend(knumbers)
        all_devices_info.extend(devices_info)
        
        logger.info(f"Processed {len(knumbers)} K-numbers from batch file")
    
    # Remove duplicates but preserve order
    unique_knumbers = []
    seen = set()
    for knumber in all_knumbers:
        if knumber not in seen:
            seen.add(knumber)
            unique_knumbers.append(knumber)
    
    result = {
        'knumbers': unique_knumbers,
        'devices_info': all_devices_info,
        'total_knumbers': len(unique_knumbers),
        'total_devices': len(all_devices_info)
    }
    
    logger.info(f"Total unique K-numbers: {result['total_knumbers']}")
    logger.info(f"Total device records: {result['total_devices']}")
    
    return result 