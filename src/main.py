#!/usr/bin/env python3
"""
Predicate Device Analyzer API

A REST API to extract predicate device relationships from FDA 510(k) PDFs.
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
import uvicorn

# Add the parent directory to sys.path to allow imports from the project
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import setup_logging
from src.pdf.utils import get_pdf_url, fetch_pdf_content, parse_pdf
from src.pdf.processor import process_pdf_for_predicates, normalize_knumber
from src.db.mongodb import (
    test_mongodb_connection, 
    get_device_by_knumber, 
    save_device_to_mongodb,
    initialize_db_connection
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Predicate Device Analyzer API",
    description="API for extracting predicate device relationships from FDA 510(k) PDFs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://predicate-graph.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# OpenFDA API settings
OPENFDA_API_BASE_URL = "https://api.fda.gov/device/510k.json"
DEFAULT_TIMEOUT = 30  # seconds

# Initialize MongoDB connection once at startup
mongodb_available = initialize_db_connection()
if not mongodb_available:
    logger.warning("MongoDB connection failed - some features will be limited")
else:
    logger.info("MongoDB connection initialized successfully")

# Define response models using Pydantic
class DeviceResponse(BaseModel):
    k_number: str = Field(..., description="The K-number of the device")
    applicant: Optional[str] = Field(None, description="The applicant/manufacturer name")
    decision_date: Optional[str] = Field(None, description="The decision date (YYYY-MM-DD)")
    decision_description: Optional[str] = Field(None, description="The decision description")
    device_name: Optional[str] = Field(None, description="The device name")
    product_code: Optional[str] = Field(None, description="The product code")
    statement_or_summary: Optional[str] = Field(None, description="Type of document (Statement or Summary)")
    predicate_devices: List[str] = Field(default_factory=list, description="List of predicate device K-numbers")

async def fetch_device_from_openfda(k_number: str) -> Dict[str, Any]:
    """
    Fetch device information from the OpenFDA API
    
    Args:
        k_number: The K-number to search for
        
    Returns:
        Dictionary with device information
        
    Raises:
        HTTPException: If the device is not found or other API errors occur
    """
    try:
        # Build the API URL with the k_number as search parameter
        url = f"{OPENFDA_API_BASE_URL}?search=k_number:{k_number}&limit=1"
        
        # Make the API request
        logger.info(f"Fetching device information for {k_number} from OpenFDA API")
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        
        # Check for successful response
        if response.status_code == 200:
            data = response.json()
            
            # Check if results exist
            if data.get('results') and len(data['results']) > 0:
                return data['results'][0]
            else:
                logger.warning(f"No results found for K-number {k_number}")
                raise HTTPException(status_code=404, detail=f"Device with K-number {k_number} not found")
        
        elif response.status_code == 404:
            logger.warning(f"Device with K-number {k_number} not found in OpenFDA")
            raise HTTPException(status_code=404, detail=f"Device with K-number {k_number} not found")
        
        else:
            logger.error(f"Error fetching device from OpenFDA: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, 
                                detail=f"Error from OpenFDA API: {response.text}")
            
    except requests.RequestException as e:
        logger.error(f"Request error when fetching device from OpenFDA: {str(e)}")
        raise HTTPException(status_code=503, detail="Service Unavailable: Unable to connect to OpenFDA API")

async def extract_predicates_from_pdf(k_number: str) -> List[str]:
    """
    Extract predicate devices from PDF for a given K-number
    
    Args:
        k_number: The K-number to get predicates for
        
    Returns:
        List of predicate device K-numbers found in the PDF
    """
    try:
        # Get the PDF URL
        url = get_pdf_url(k_number)
        logger.info(f"Checking PDF for {k_number} at {url}")
        
        # Download the PDF without saving to disk
        pdf_content = fetch_pdf_content(url)
        
        if not pdf_content:
            logger.info(f"No PDF found for {k_number}")
            return []
        
        logger.info(f"PDF content retrieved for {k_number}, size: {len(pdf_content)} bytes")
        
        # Parse the PDF
        parsed_data = parse_pdf(pdf_content)
        logger.info(f"PDF parsed for {k_number}, {parsed_data.get('pages', 0)} pages")
        
        # Extract predicate device information
        predicates = process_pdf_for_predicates(parsed_data, device_k_number=k_number)
        
        if predicates:
            logger.info(f"Found {len(predicates)} predicate device(s) for {k_number}: {', '.join(predicates)}")
        else:
            logger.info(f"No predicate devices found for {k_number}, checking text sample")
            # Debugging: Check a sample of the text to see if key phrases are present
            text_sample = parsed_data.get('text', '')[:5000]
            logger.info(f"Text sample from PDF: {text_sample[:200]}...")
            
        return predicates
        
    except Exception as e:
        logger.error(f"Error extracting predicates from PDF for {k_number}: {str(e)}")
        logger.exception(e)  # Log the full exception with traceback
        return []

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint that redirects to the documentation."""
    return {"message": "Welcome to the Predicate Device Analyzer API. Visit /docs for API documentation."}

@app.get("/api/device/{k_number}", response_model=DeviceResponse, 
         summary="Get device information with predicate relationships",
         description="Fetch device information from OpenFDA and extract predicate relationships from PDF summary")
async def get_device(k_number: str, refresh_predicates: bool = False):
    """
    Get device information and its predicate relationships.
    
    This endpoint:
    1. Fetches device information from the OpenFDA API
    2. Checks if a PDF summary exists for the device
    3. If a PDF exists, extracts predicate device relationships
    
    Args:
        k_number: The K-number of the FDA 510(k) device
        refresh_predicates: If true, force re-extraction of predicates even if in MongoDB
        
    Returns:
        DeviceResponse: Device information with predicate relationships
    """
    # Normalize K-number format
    k_number = normalize_knumber(k_number)
    
    logger.info(f"Processing request for device {k_number}")
    
    existing_device = None
    
    # Check if MongoDB is available and device exists
    if mongodb_available:
        try:
            existing_device = get_device_by_knumber(k_number)
            if existing_device:
                logger.info(f"Found device with K-number {k_number} in MongoDB with {len(existing_device.get('predicate_devices', []))} predicates")
        except Exception as e:
            logger.error(f"Error querying MongoDB: {e}")
            existing_device = None
    else:
        logger.info("MongoDB not available, skipping database check")
    
    # Determine if we need to refresh predicates
    needs_predicate_refresh = (
        refresh_predicates or 
        not existing_device or 
        not existing_device.get('predicate_devices') or 
        len(existing_device.get('predicate_devices', [])) == 0
    )
    
    if existing_device and not needs_predicate_refresh:
        # Remove MongoDB ID field
        existing_device.pop("_id", None)
        return existing_device
    
    # We need to fetch device info or refresh predicates
    predicate_devices = []
    
    if needs_predicate_refresh:
        # Extract predicate devices from PDF
        logger.info(f"Extracting predicate devices for {k_number}")
        predicate_devices = await extract_predicates_from_pdf(k_number)
        logger.info(f"Predicate extraction complete for {k_number}: {predicate_devices}")
    
    # If we have an existing device, update it with new predicates
    if existing_device and needs_predicate_refresh and mongodb_available:
        try:
            existing_device.pop("_id", None)
            existing_device["predicate_devices"] = predicate_devices
            
            # Update MongoDB using save function
            save_success = save_device_to_mongodb(existing_device)
            
            if save_success:
                logger.info(f"Updated device {k_number} in MongoDB with {len(predicate_devices)} predicates")
            else:
                logger.warning(f"Failed to update device {k_number} in MongoDB")
                
            return existing_device
        except Exception as e:
            logger.error(f"Error updating MongoDB: {e}")
            # Continue with fetching from OpenFDA
    
    # If we get here, we need to fetch the device info from OpenFDA
    device_info = await fetch_device_from_openfda(k_number)
    logger.info(f"Fetched device info from OpenFDA for {k_number}")
    
    # Create the response object
    response = {
        "k_number": device_info.get("k_number", k_number),
        "applicant": device_info.get("applicant", ""),
        "decision_date": device_info.get("decision_date", ""),
        "decision_description": device_info.get("decision_description", ""),
        "device_name": device_info.get("device_name", ""),
        "product_code": device_info.get("product_code", ""),
        "statement_or_summary": device_info.get("statement_or_summary", ""),
        "predicate_devices": predicate_devices
    }
    
    # Save to MongoDB if available
    if mongodb_available:
        save_success = save_device_to_mongodb(response)
        if save_success:
            logger.info(f"Saved device {k_number} to MongoDB")
        else:
            logger.warning(f"Failed to save device {k_number} to MongoDB")
    
    logger.info(f"Returning response for {k_number} with {len(predicate_devices)} predicates")
    return response

@app.post("/api/device", response_model=DeviceResponse,
         summary="Save device information to MongoDB",
         description="Save device information with predicate relationships to MongoDB")
async def save_device(device: DeviceResponse = Body(...)):
    """
    Save device information to MongoDB.
    
    Args:
        device: The device information to save
        
    Returns:
        DeviceResponse: The saved device information
    """
    if not mongodb_available:
        raise HTTPException(status_code=503, detail="MongoDB not available")
        
    try:
        # Convert the Pydantic model to a dictionary
        device_dict = device.dict()
        
        # Ensure K-number is normalized
        device_dict["k_number"] = normalize_knumber(device_dict["k_number"])
        
        # Save device using the db module function
        save_success = save_device_to_mongodb(device_dict)
        
        if not save_success:
            raise Exception("Failed to save device to MongoDB")
            
        logger.info(f"Saved device with K-number {device_dict['k_number']} to MongoDB")
        
        return device
    
    except Exception as e:
        logger.error(f"Error saving device to MongoDB: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving device to MongoDB: {str(e)}")

@app.get("/api/device/check/{k_number}", 
         summary="Check if device exists in MongoDB",
         description="Check if a device with the given K-number exists in MongoDB")
async def check_device(k_number: str):
    """
    Check if a device exists in MongoDB.
    
    Args:
        k_number: The K-number to check
        
    Returns:
        Dict with exists flag and k_number
    """
    # Normalize K-number format
    k_number = normalize_knumber(k_number)
    
    if not mongodb_available:
        return {
            "exists": False,
            "k_number": k_number,
            "error": "MongoDB not available"
        }
        
    try:
        # Check if device exists in MongoDB using db module function
        existing_device = get_device_by_knumber(k_number)
        
        return {
            "exists": existing_device is not None,
            "k_number": k_number
        }
    except Exception as e:
        logger.error(f"Error checking device in MongoDB: {str(e)}")
        return {
            "exists": False,
            "k_number": k_number,
            "error": f"MongoDB error: {str(e)}"
        }

@app.get("/api/health", summary="Health check endpoint", 
         description="Endpoint to check if the API is running correctly")
async def health_check():
    """Health check endpoint to verify the API is working."""
    # Include MongoDB status in health check
    db_status = test_mongodb_connection()
    
    return {
        "status": "ok", 
        "version": "1.0.0",
        "mongodb": {
            "connected": db_status["success"],
            "database": db_status["database"],
            "device_count": db_status["device_count"] if db_status["success"] else 0
        }
    }

def main():
    """Start the FastAPI application with uvicorn server."""
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Get host from environment variable or use default
    host = os.environ.get("HOST", "0.0.0.0")
    
    # Start the uvicorn server
    uvicorn.run("src.main:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    main() 