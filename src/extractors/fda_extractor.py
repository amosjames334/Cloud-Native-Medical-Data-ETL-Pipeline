"""
FDA Data Extractor
Extracts drug event data from FDA OpenFDA API
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import time
import os
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FDAExtractor:
    """Extract data from FDA OpenFDA API"""
    
    BASE_URL = "https://api.fda.gov/drug/drugsfda.json"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FDA extractor
        
        Args:
            api_key: Optional FDA API key for higher rate limits
        """
        self.api_key = api_key or os.getenv('FDA_API_KEY')
        self.session = requests.Session()
        
    def extract_drug_events(
        self, 
        start_date: str, 
        end_date: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Extract drug details from FDA Drugs@FDA API
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Maximum number of records to fetch
            
        Returns:
            DataFrame with drug details
        """
        # Initialize params dictionary
        params = {}
        if self.api_key:
            params['api_key'] = self.api_key
            
        # Format dates for FDA API (YYYYMMDD)
        start_str = start_date.replace('-', '')
        end_str = end_date.replace('-', '')
        
        # Construct search query for submissions in the date range
        params['search'] = f'submissions.submission_status_date:[{start_str} TO {end_str}]'
        
        all_records = []
        skip = 0
        
        # FDA API limit per request is 99
        batch_size = 99
        
        while len(all_records) < limit:
            params['skip'] = skip
            params['limit'] = min(limit - len(all_records), batch_size)
            
            try:
                response = self._make_request(params)
                
                if 'results' not in response:
                    logger.warning("No results in response")
                    break
                
                results = response['results']
                all_records.extend(results)
                
                logger.info(f"Fetched {len(results)} records (total: {len(all_records)})")
                
                # Check if we've reached the end
                if len(results) < params['limit']:
                    break
                
                skip += len(results)
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching data: {e}")
                break
        
        # Convert to DataFrame
        df = self._parse_records(all_records)
        logger.info(f"Extracted {len(df)} FDA records")
        
        return df
    
    def _make_request(self, params: dict) -> dict:
        """Make API request with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    raise
    
    def _parse_records(self, records: list) -> pd.DataFrame:
        """Parse FDA drug records into structured DataFrame"""
        parsed_data = []
        
        for record in records:
            try:
                # Extract key fields from Drugs@FDA schema
                parsed = {
                    'application_number': record.get('application_number'),
                    'sponsor_name': record.get('sponsor_name'),
                    'openfda_brand_name': None,
                    'openfda_generic_name': None,
                    'openfda_manufacturer_name': None
                }
                
                # Extract OpenFDA fields if available
                openfda = record.get('openfda', {})
                if openfda:
                    parsed['openfda_brand_name'] = ', '.join(openfda.get('brand_name', []))
                    parsed['openfda_generic_name'] = ', '.join(openfda.get('generic_name', []))
                    parsed['openfda_manufacturer_name'] = ', '.join(openfda.get('manufacturer_name', []))
                
                # Extract product details (taking the first one for simplicity, or could explode)
                products = record.get('products', [])
                if products:
                    product = products[0]
                    parsed['brand_name'] = product.get('brand_name')
                    parsed['active_ingredients'] = ', '.join([item.get('name', '') for item in product.get('active_ingredients', [])])
                    parsed['dosage_form'] = product.get('dosage_form')
                    parsed['marketing_status'] = product.get('marketing_status')
                
                # Extract latest submission date
                submissions = record.get('submissions', [])
                if submissions:
                    # Sort by date descending
                    submissions.sort(key=lambda x: x.get('submission_status_date', ''), reverse=True)
                    parsed['latest_submission_date'] = submissions[0].get('submission_status_date')
                    parsed['submission_type'] = submissions[0].get('submission_type')
                
                parsed_data.append(parsed)
                
            except Exception as e:
                logger.warning(f"Error parsing record {record.get('application_number')}: {e}")
                continue
        
        df = pd.DataFrame(parsed_data)
        
        # Data type conversions
        if not df.empty and 'latest_submission_date' in df.columns:
            df['latest_submission_date'] = pd.to_datetime(df['latest_submission_date'], format='%Y%m%d', errors='coerce')
            
        return df
    
    def _extract_age(self, patient: dict) -> Optional[float]:
        """Deprecated: Extract and normalize patient age (kept for compatibility if needed)"""
        return None


if __name__ == '__main__':
    # Test the extractor
    extractor = FDAExtractor()
    data = extractor.extract_drug_events(
        start_date='2025-01-01',
        end_date='2025-01-30',
        limit=10
    )
    print(f"Extracted {len(data)} records")
    print(data.head())