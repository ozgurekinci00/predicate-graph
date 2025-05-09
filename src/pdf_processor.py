#!/usr/bin/env python3
"""
PDF processor module for extracting predicate device information.

This module contains functions to extract predicate device K-numbers from PDF text.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set

from src.processors import normalize_knumber

# Setup logging
logger = logging.getLogger(__name__)

def extract_k_number_pattern(text: str) -> List[str]:
    """
    Extract K-numbers using regex pattern matching.
    
    Args:
        text: The text content to search
        
    Returns:
        List of K-numbers found
    """
    # Standard pattern for K-numbers: K followed by 6 digits, with or without leading zeros
    standard_pattern = r'\bK\s*\d{6,}\b|\bK\s*\d{3}\s*\d{3,}\b'
    
    # Additionally, look for common OCR errors where 'O' is used instead of '0'
    # I found an example for K163547, one of the predicates is written with the letter 'O' instead of number '0'
    # This pattern looks for K followed by a mix of digits and the letter 'O'
    ocr_error_pattern = r'\bK\s*[O0-9]{6,}\b'
    
    # Find all matches for both patterns
    standard_matches = re.findall(standard_pattern, text, re.IGNORECASE)
    ocr_error_matches = re.findall(ocr_error_pattern, text, re.IGNORECASE)
    
    # Combine all matches
    all_matches = standard_matches + ocr_error_matches
    
    # Clean up the matches: remove spaces, ensure uppercase K, correct OCR errors
    k_numbers = []
    for match in all_matches:
        # Remove spaces
        cleaned = re.sub(r'\s+', '', match).upper()
        
        # Correct common OCR errors - replace letter 'O' with digit '0' after the K
        if re.match(r'^K[O0-9]{6}$', cleaned):
            cleaned = 'K' + cleaned[1:].replace('O', '0')
        
        # Only keep it if it now matches the standard K-number format
        if re.match(r'^K\d{6}$', cleaned):
            k_numbers.append(cleaned)
    
    # Remove duplicates while preserving order
    unique_k_numbers = []
    seen = set()
    for k in k_numbers:
        if k not in seen:
            unique_k_numbers.append(k)
            seen.add(k)
    
    return unique_k_numbers

def extract_predicate_devices(text: str, device_k_number: Optional[str] = None) -> List[str]:
    """
    Extract predicate device K-numbers from PDF text.
    
    Args:
        text: The text content of the PDF
        device_k_number: The K-number of the device being analyzed (to exclude from results)
        
    Returns:
        List of predicate device K-numbers
    """
    predicate_devices = set()
    
    # Break the text into lines to make it easier to process
    lines = text.split('\n')
    
    # List of patterns that indicate predicate devices
    predicate_patterns = [
        r'predicate\s+device',
        r'primary\s+predicate\s+device',
        r'reference\s+predicate\s+device',
        r'substantially\s+equivalent\s+device',
        r'equivalent\s+legally\s+marketed\s+device',
        r'reference\s+device',
        r'comparable\s+device',
        r'previously\s+cleared\s+device',
    ]
    
    # Pattern for K-numbers
    k_pattern = r'K\d{6}'
    
    # First, look for lines containing predicate device phrases
    potential_lines = []
    for i, line in enumerate(lines):
        for pattern in predicate_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Add this line and a few following lines to check for K-numbers
                potential_lines.extend([(i, line)] + [(i+j, lines[i+j]) for j in range(1, 4) if i+j < len(lines)])
                break
    
    # Now check these lines for K-numbers
    for i, line in potential_lines:
        k_numbers = extract_k_number_pattern(line)
        for k in k_numbers:
            predicate_devices.add(k)
    
    # Look for table-formatted predicate devices
    # This is complex and might need context from surrounding rows/columns
    table_indicators = [
        # Check for table headers suggesting predicate device columns
        r'(predicate|reference|equivalent)\s*device',
        r'510\(k\)\s*number',
        r'k\s*number',
        r'substantial\s*equivalence',
        r'model'  # Many tables include "Model" as a column header alongside K-numbers
    ]
    
    table_sections = []
    for i, line in enumerate(lines):
        for indicator in table_indicators:
            if re.search(indicator, line, re.IGNORECASE):
                # If we find a table header, mark this as a potential table section
                table_sections.append((max(0, i-2), min(len(lines), i+20)))  # Expanded range to capture more of the table
                break
    
    # Process all identified table sections
    for start, end in table_sections:
        table_text = "\n".join(lines[start:end])
        # Extract all K-numbers from the table section
        k_numbers = extract_k_number_pattern(table_text)
        for k in k_numbers:
            predicate_devices.add(k)
        
        # Special handling for tables with rows containing K-numbers
        # Look for rows that might contain K-numbers (often formatted differently)
        for i in range(start, end):
            line = lines[i]
            # Check if this line could be a table row with a K-number
            if re.search(r'K\d{6}', line, re.IGNORECASE):
                # Examine this line carefully
                line_k_numbers = extract_k_number_pattern(line)
                for k in line_k_numbers:
                    predicate_devices.add(k)
                    
                    # Sometimes table cells can span across multiple lines
                    # Check if the next line might continue this entry
                    if i+1 < end:
                        next_line = lines[i+1]
                        if not re.search(r'K\d{6}', next_line, re.IGNORECASE) and not re.search(r'^\s*$', next_line):
                            # If the next line doesn't have a K-number and isn't just whitespace
                            # it might contain relevant information like model names
                            # This helps with complex tables that span multiple lines
                            next_line_k_numbers = extract_k_number_pattern(next_line)
                            for k in next_line_k_numbers:
                                predicate_devices.add(k)
    
    # Additional pass to find K-numbers in sections that might mention predicates
    # but without using the exact phrases we checked earlier
    section_start_indices = []
    section_patterns = [
        r'(?i)comparable\s+device',
        r'(?i)equivalent\s+device',
        r'(?i)reference\s+device',
        r'(?i)predicate\s+identification',
        r'(?i)substantial\s+equivalence',
    ]
    
    for i, line in enumerate(lines):
        for pattern in section_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                section_start_indices.append(i)
    
    for start_idx in section_start_indices:
        # Check the next few lines after each section start
        end_idx = min(start_idx + 15, len(lines))
        for i in range(start_idx, end_idx):
            k_numbers = extract_k_number_pattern(lines[i])
            for k in k_numbers:
                predicate_devices.add(k)
    
    # Remove the device's own K-number if it appears in the list and was provided
    if device_k_number:
        normalized_k = normalize_knumber(device_k_number)
        if normalized_k in predicate_devices:
            predicate_devices.remove(normalized_k)
    
    return list(predicate_devices)

def process_pdf_for_predicates(pdf_data: Dict[str, Any], device_k_number: Optional[str] = None) -> List[str]:
    """
    Process parsed PDF data to extract predicate device K-numbers.
    
    Args:
        pdf_data: Dictionary containing parsed PDF data
        device_k_number: The K-number of the device being analyzed (to exclude from results)
        
    Returns:
        List of predicate device K-numbers
    """
    predicates = []
    
    if not pdf_data or not pdf_data.get('parseable'):
        logger.warning("PDF data is not parseable")
        return predicates
    
    text = pdf_data.get('text', '')
    if not text:
        logger.warning("No text found in PDF data")
        return predicates
    
    predicates = extract_predicate_devices(text, device_k_number)
    return predicates

def analyze_predicate_relationships(device_k_number: str, predicates: List[str]) -> Dict[str, Any]:
    """
    Analyze predicate relationships between the device and its predicates.
    
    Args:
        device_k_number: The K-number of the device
        predicates: List of predicate device K-numbers
        
    Returns:
        Dictionary with relationship information
    """
    return {
        'device': device_k_number,
        'predicates': predicates,
        'count': len(predicates)
    } 