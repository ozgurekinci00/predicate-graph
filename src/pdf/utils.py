#!/usr/bin/env python3
"""
PDF utility module for extracting predicate device information.

This module handles retrieving, parsing, and analyzing PDF summaries for K-numbers.
"""

import logging
import requests
import PyPDF2
from io import BytesIO
from typing import Dict, Optional, Any

from src.pdf.processor import normalize_knumber, process_pdf_for_predicates

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
    
    # Extract year information from K-number
    year_part = k_number[1:3]
    
    # Convert to integer for comparison
    year_num = int(year_part)
    
    # Determine the PDF path component based on year
    if year_num < 2 or year_num >= 76:
        # Pre-2002 (K00xxxx, K01xxxx) and all pre-2000 (K76xxxx to K99xxxx) use "pdf/"
        pdf_path = "pdf"
    else:
        # 2002+ (K02xxxx and above) use "pdf2/", "pdf15/", etc.
        pdf_path = f"pdf{year_num}"
    
    # Construct the full URL
    url = f"https://www.accessdata.fda.gov/cdrh_docs/{pdf_path}/{k_number}.pdf"
    
    logger.debug(f"Generated URL for {k_number}: {url}")
    
    return url

def fetch_pdf_content(url: str) -> Optional[bytes]:
    """
    Fetch a PDF file's content from a URL
    
    Args:
        url: The URL of the PDF
    
    Returns:
        The PDF content as bytes if found, None otherwise
    """
    try:
        response = requests.get(url, timeout=20)
        
        # Check if request was successful and returned a PDF
        if response.status_code == 200 and response.headers.get('Content-Type', '').lower().startswith('application/pdf'):
            # Return the PDF content
            return response.content
        else:
            logger.info(f"No PDF found at {url} (Status code: {response.status_code})")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error fetching PDF from {url}: {str(e)}")
        return None

def parse_pdf(pdf_content: bytes) -> Dict[str, Any]:
    """
    Parse a PDF file for relevant information
    
    Args:
        pdf_content: The PDF content as bytes
    
    Returns:
        A dictionary containing extracted text and metadata
    """
    result = {
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

def get_pdf_predicates(k_number: str) -> Dict[str, Any]:
    """
    Retrieve and analyze a PDF to extract predicate device information
    
    Args:
        k_number: The K-number to analyze
    
    Returns:
        Dictionary with PDF information and predicate devices
    """
    k_number = normalize_knumber(k_number)
    result = {
        'k_number': k_number,
        'pdf_exists': False,
        'pdf_url': None,
        'predicates': []
    }
    
    # Generate the URL for the PDF
    url = get_pdf_url(k_number)
    result['pdf_url'] = url
    
    logger.info(f"Checking PDF for {k_number} at {url}")
    
    # Fetch the PDF content
    pdf_content = fetch_pdf_content(url)
    
    if pdf_content:
        result['pdf_exists'] = True
        
        # Parse the PDF
        parsed_data = parse_pdf(pdf_content)
        
        # Extract predicate device information
        predicates = process_pdf_for_predicates(parsed_data, device_k_number=k_number)
        result['predicates'] = predicates
        
        if predicates:
            logger.info(f"Found {len(predicates)} predicate device(s) for {k_number}: {', '.join(predicates)}")
        else:
            logger.info(f"No predicate devices found for {k_number}")
    
    return result
