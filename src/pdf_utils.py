#!/usr/bin/env python3
"""
PDF utility module for the Predicate Relationships Graph.

This module handles retrieving and parsing PDF summaries for K-numbers.
"""

import os
import logging
import requests
import PyPDF2
from io import BytesIO
from typing import Dict, Optional, List, Tuple, Any, Union
import re

from src.config import DATA_DIR, PDF_DIR
from src.processors import normalize_knumber
from src.pdf_processor import process_pdf_for_predicates

# Setup logging
logger = logging.getLogger(__name__)

def get_pdf_url(k_number: str) -> str:
    """
    Generate the URL for a K-number's PDF summary based on FDA URL pattern
    
    Args:
        k_number: The K-number (e.g., K231101)
    
    Returns:
        The URL where the PDF might be found
    """
    k_number = normalize_knumber(k_number)
    
    # Check if the K-number follows the standard format
    if not re.match(r'^K\d{6}$', k_number):
        logger.warning(f"Non-standard K-number format: {k_number}")
        # For non-standard K-numbers, use the pdf/ path as fallback
        pdf_path = "pdf"
    else:
        # Extract year information from K-number
        year_part = k_number[1:3]
        
        try:
            # Convert to integer for comparison
            year_num = int(year_part)
            
            # Determine the PDF path component based on year
            if year_num < 2 or year_num >= 76:
                # Pre-2002 (K00xxxx, K01xxxx) and all pre-2000 (K76xxxx to K99xxxx) use "pdf/"
                pdf_path = "pdf"
            elif 2 <= year_num <= 9:
                # 2002-2009 (K02xxxx to K09xxxx) use "pdf2/" to "pdf9/"
                pdf_path = f"pdf{year_num}"
            else:
                # 2010+ (K10xxxx and above) use "pdf10/", "pdf11/", etc.
                pdf_path = f"pdf{year_num}"
        except ValueError:
            # If we can't parse the year, use the pdf/ path as fallback
            logger.warning(f"Could not parse year from K-number: {k_number}")
            pdf_path = "pdf"
    
    # Construct the full URL
    url = f"https://www.accessdata.fda.gov/cdrh_docs/{pdf_path}/{k_number}.pdf"
    
    logger.debug(f"Generated URL for {k_number}: {url}")
    
    return url

def download_pdf(url: str, save_path: Optional[str] = None) -> Optional[bytes]:
    """
    Download a PDF file from a URL and optionally save it to disk
    
    Args:
        url: The URL of the PDF
        save_path: Path to save the PDF (if None, PDF is not saved to disk)
    
    Returns:
        The PDF content as bytes if found, None otherwise
    """
    try:
        response = requests.get(url, timeout=10)
        
        # Check if request was successful and returned a PDF
        if response.status_code == 200 and response.headers.get('Content-Type', '').lower().startswith('application/pdf'):
            # Save the PDF if a path was provided
            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"PDF saved to {save_path}")
            
            # Return the PDF content regardless of whether it was saved
            return response.content
        else:
            logger.info(f"No PDF found at {url} (Status code: {response.status_code})")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error downloading PDF from {url}: {str(e)}")
        return None

def parse_pdf(pdf_content: bytes) -> Dict[str, Any]:
    """
    Parse a PDF file for relevant information
    
    Args:
        pdf_content: The PDF content as bytes
    
    Returns:
        A dictionary containing extracted information
    """
    result = {
        'parseable': False,
        'text': '',
        'pages': 0,
        'metadata': {}
    }
    
    try:
        # Create a PDF file object from bytes
        pdf_file = BytesIO(pdf_content)
        
        # Create PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract basic information
        result['pages'] = len(pdf_reader.pages)
        result['metadata'] = pdf_reader.metadata or {}
        result['parseable'] = True
        
        # Extract text from all pages
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        
        result['text'] = text
        
        logger.info(f"Successfully parsed PDF ({result['pages']} pages)")
        
    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
        result['error'] = str(e)
    
    return result

def check_pdf_for_knumber(k_number: str, download: bool = True, extract_predicates: bool = True) -> Dict[str, Any]:
    """
    Check if a PDF summary exists for a K-number and optionally download and parse it
    
    Args:
        k_number: The K-number to check
        download: Whether to download the PDF if found (if False, will only parse but not save)
        extract_predicates: Whether to extract predicate device information
    
    Returns:
        A dictionary with PDF information and parsed content if available
    """
    k_number = normalize_knumber(k_number)
    result = {
        'k_number': k_number,
        'pdf_exists': False,
        'pdf_url': None,
        'pdf_path': None,
        'pdf_content': None,
        'parsed_data': None,
        'predicate_devices': []
    }
    
    # Generate the URL for the PDF
    url = get_pdf_url(k_number)
    result['pdf_url'] = url
    
    logger.info(f"Checking PDF for {k_number} at {url}")
    
    # Determine the save path if downloading is enabled
    save_path = None
    if download:
        save_path = os.path.join(PDF_DIR, f"{k_number}.pdf")
        result['pdf_path'] = save_path
    
    # Download the PDF
    pdf_content = download_pdf(url, save_path if download else None)
    
    if pdf_content:
        result['pdf_exists'] = True
        
        # Always parse the PDF if it was found, regardless of download setting
        result['parsed_data'] = parse_pdf(pdf_content)
        
        # Extract predicate device information if requested
        if extract_predicates and result['parsed_data'] and result['parsed_data']['parseable']:
            predicates = process_pdf_for_predicates(result['parsed_data'], device_k_number=k_number)
            result['predicate_devices'] = predicates
            if predicates:
                logger.info(f"Found {len(predicates)} predicate device(s) for {k_number}: {', '.join(predicates)}")
            else:
                logger.info(f"No predicate devices found for {k_number}")
    
    return result

def process_knumbers_for_pdfs(k_numbers: List[str], download: bool = True, parse_only: bool = False, extract_predicates: bool = True) -> List[Dict[str, Any]]:
    """
    Process a list of K-numbers to check for PDFs
    
    Args:
        k_numbers: List of K-numbers to check
        download: Whether to download and save found PDFs to disk
        parse_only: If True, will parse PDFs without saving them (overrides download if True)
        extract_predicates: Whether to extract predicate device information
    
    Returns:
        List of dictionaries with PDF information for each K-number
    """
    results = []
    
    # If parse_only is True, set download to False
    if parse_only:
        download = False
    
    for k_number in k_numbers:
        result = check_pdf_for_knumber(k_number, download, extract_predicates)
        results.append(result)
    
    return results

# Test function for demonstration
def test_pdf_retrieval():
    """Test PDF retrieval for sample K-numbers"""
    k_numbers = ['K970904', 'K011958', 'K231101']
    
    logger.info(f"Testing PDF retrieval for K-numbers: {k_numbers}")
    
    results = process_knumbers_for_pdfs(k_numbers)
    
    for result in results:
        k_number = result['k_number']
        if result['pdf_exists']:
            logger.info(f"K-number {k_number}: PDF found at {result['pdf_url']}")
            if result['parsed_data'] and result['parsed_data']['parseable']:
                logger.info(f"  Parsed {result['parsed_data']['pages']} pages")
            else:
                logger.info("  PDF could not be parsed")
        else:
            logger.info(f"K-number {k_number}: No PDF found at {result['pdf_url']}")
    
    return results

if __name__ == "__main__":
    # Setup logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    
    # Run the test function
    test_pdf_retrieval() 