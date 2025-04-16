#!/usr/bin/env python3
"""
Cloud Functions for ALLMBA Daily Investment Ideas

This module handles the integration with cloud services like Google Cloud Storage.
"""

import os
import json
import logging
import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile

# Set up logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Check if we're running on GCP
try:
    from google.cloud import storage
    GCP_AVAILABLE = True
except ImportError:
    logger.warning("Google Cloud Storage library not available. Using local storage only.")
    GCP_AVAILABLE = False

# Get the bucket name from environment variable
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET")

# Local data paths
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

def is_running_on_cloud() -> bool:
    """
    Check if we're running on Google Cloud.
    """
    return all([
        GCP_AVAILABLE,
        STORAGE_BUCKET is not None,
        os.getenv("K_SERVICE") is not None  # This env var is present on Cloud Run
    ])

def get_storage_client():
    """
    Get a Google Cloud Storage client.
    """
    if not GCP_AVAILABLE:
        raise RuntimeError("Google Cloud Storage library not available")
    
    return storage.Client()

def upload_data_to_cloud(local_path: Path, cloud_path: str) -> bool:
    """
    Upload a file to Google Cloud Storage.
    
    Args:
        local_path: Local file path
        cloud_path: Path in the cloud storage bucket
        
    Returns:
        bool: Success status
    """
    if not is_running_on_cloud() or not local_path.exists():
        return False
    
    try:
        client = get_storage_client()
        bucket = client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(cloud_path)
        blob.upload_from_filename(str(local_path))
        logger.info(f"Uploaded {local_path} to gs://{STORAGE_BUCKET}/{cloud_path}")
        return True
    except Exception as e:
        logger.error(f"Error uploading to Cloud Storage: {e}")
        return False

def download_data_from_cloud(cloud_path: str, local_path: Path) -> bool:
    """
    Download a file from Google Cloud Storage.
    
    Args:
        cloud_path: Path in the cloud storage bucket
        local_path: Local file path
        
    Returns:
        bool: Success status
    """
    if not is_running_on_cloud():
        return False
    
    try:
        # Ensure the directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        client = get_storage_client()
        bucket = client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(cloud_path)
        
        if not blob.exists():
            logger.warning(f"File gs://{STORAGE_BUCKET}/{cloud_path} does not exist")
            return False
        
        blob.download_to_filename(str(local_path))
        logger.info(f"Downloaded gs://{STORAGE_BUCKET}/{cloud_path} to {local_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading from Cloud Storage: {e}")
        return False

def list_cloud_files(prefix: str) -> list:
    """
    List files in Google Cloud Storage with the given prefix.
    
    Args:
        prefix: Prefix to filter files
        
    Returns:
        list: List of file paths
    """
    if not is_running_on_cloud():
        return []
    
    try:
        client = get_storage_client()
        bucket = client.bucket(STORAGE_BUCKET)
        blobs = list(bucket.list_blobs(prefix=prefix))
        return [blob.name for blob in blobs]
    except Exception as e:
        logger.error(f"Error listing files in Cloud Storage: {e}")
        return []

def load_investment_ideas_from_cloud(date: Optional[str] = None) -> Dict[str, Any]:
    """
    Load investment ideas from Google Cloud Storage.
    
    Args:
        date: Date string in YYYY-MM-DD format
        
    Returns:
        dict: Investment ideas data
    """
    if not is_running_on_cloud():
        # Fall back to local loading
        return None
    
    try:
        if date:
            # Try to get the specific date
            cloud_path = f"processed/investment_ideas_{date}.json"
            local_path = Path(tempfile.gettempdir()) / f"investment_ideas_{date}.json"
            
            if download_data_from_cloud(cloud_path, local_path):
                with open(local_path, 'r') as f:
                    data = json.load(f)
                    
                    # Add ID field to each idea
                    for i, idea in enumerate(data.get("ideas", [])):
                        idea["id"] = f"{data.get('date', 'unknown')}-{i+1}"
                    
                    return data
        else:
            # Find the latest file
            files = list_cloud_files("processed/investment_ideas_")
            if not files:
                return None
            
            # Sort by name (which includes the date)
            files.sort(reverse=True)
            latest_cloud_path = files[0]
            latest_local_path = Path(tempfile.gettempdir()) / Path(latest_cloud_path).name
            
            if download_data_from_cloud(latest_cloud_path, latest_local_path):
                with open(latest_local_path, 'r') as f:
                    data = json.load(f)
                    
                    # Add ID field to each idea
                    for i, idea in enumerate(data.get("ideas", [])):
                        idea["id"] = f"{data.get('date', 'unknown')}-{i+1}"
                    
                    return data
    
    except Exception as e:
        logger.error(f"Error loading investment ideas from cloud: {e}")
    
    return None

def get_available_dates_from_cloud() -> list:
    """
    Get available dates for investment ideas from Google Cloud Storage.
    
    Returns:
        list: List of date strings
    """
    if not is_running_on_cloud():
        return []
    
    try:
        files = list_cloud_files("processed/investment_ideas_")
        dates = []
        
        for file_path in files:
            try:
                # Extract date from filename
                filename = Path(file_path).name
                date = filename.replace("investment_ideas_", "").replace(".json", "")
                dates.append(date)
            except Exception:
                pass
        
        return sorted(dates, reverse=True)
    except Exception as e:
        logger.error(f"Error getting available dates from cloud: {e}")
        return []

def update_investment_data() -> bool:
    """
    Trigger a data update by running the collection and analysis pipeline,
    then upload results to Google Cloud Storage.
    
    Returns:
        bool: Success status
    """
    # Dynamic import to avoid circular imports
    import importlib
    collect_module = importlib.import_module("src.collect_data")
    analyze_module = importlib.import_module("src.analyze_data")
    
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Starting data update for {today}")
        
        # Create data directories
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Run data collection
        logger.info("Running data collection")
        collect_module.main()
        
        # Run data analysis
        logger.info("Running data analysis")
        analyze_module.main()
        
        # Upload results to Cloud Storage if running on GCP
        if is_running_on_cloud():
            logger.info("Uploading results to Cloud Storage")
            
            # Upload raw data files
            for file_path in RAW_DATA_DIR.glob("*_*.json"):
                cloud_path = f"raw/{file_path.name}"
                upload_data_to_cloud(file_path, cloud_path)
            
            # Upload processed data files
            for file_path in PROCESSED_DATA_DIR.glob("*_*.json"):
                cloud_path = f"processed/{file_path.name}"
                upload_data_to_cloud(file_path, cloud_path)
        
        logger.info("Data update completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating investment data: {e}")
        return False
