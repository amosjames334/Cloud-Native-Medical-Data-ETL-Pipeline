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
    
    BASE_URL = "https://api.fda.gov/drug/event.json"
    
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
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Extract drug adverse event reports
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Maximum number of records to fetch
            
        Returns:
            DataFrame with drug event data
        """
        logger.info(f"Extracting FDA data from {start_date} to {end_date}")
        
        # Convert dates to FDA format (YYYYMMDD)
        start_fda = start_date.replace('-', '')
        end_fda = end_date.replace('-', '')
        
        # Build query
        search_query = f"receivedate:[{start_fda}+TO+{end_fda}]"
        
        params = {
            'search': search_query,
            'limit': min(limit, 1000)  # FDA max is 1000 per request
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        all_records = []
        skip = 0
        
        while len(all_records) < limit:
            params['skip'] = skip
            
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
                
                skip += params['limit']
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching data: {e}")
                break
        
        # Convert to DataFrame
        df = self._parse_records(all_records[:limit])
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
        """Parse FDA records into structured DataFrame"""
        parsed_data = []
        
        for record in records:
            try:
                # Extract key fields
                parsed = {
                    'safetyreportid': record.get('safetyreportid'),
                    'receivedate': record.get('receivedate'),
                    'serious': record.get('serious', 0),
                    'seriousnessdeath': record.get('seriousnessdeath', 0),
                    'seriousnesshospitalization': record.get('seriousnesshospitalization', 0),
                    'transmissiondate': record.get('transmissiondate'),
                    'primarysource_qualification': record.get('primarysource', {}).get('qualification'),
                    'reporterorganization': record.get('primarysource', {}).get('reportercountry')
                }
                
                # Extract patient information
                patient = record.get('patient', {})
                parsed['patient_age'] = self._extract_age(patient)
                parsed['patient_sex'] = patient.get('patientsex')
                
                # Extract drug information
                drugs = patient.get('drug', [])
                if drugs:
                    parsed['drug_name'] = drugs[0].get('medicinalproduct', '')
                    parsed['drug_indication'] = drugs[0].get('drugindication', '')
                
                # Extract reactions
                reactions = patient.get('reaction', [])
                if reactions:
                    parsed['reaction'] = reactions[0].get('reactionmeddrapt', '')
                
                parsed_data.append(parsed)
                
            except Exception as e:
                logger.warning(f"Error parsing record {record.get('safetyreportid')}: {e}")
                continue
        
        df = pd.DataFrame(parsed_data)
        
        # Data type conversions
        if not df.empty:
            df['receivedate'] = pd.to_datetime(df['receivedate'], format='%Y%m%d', errors='coerce')
            df['transmissiondate'] = pd.to_datetime(df['transmissiondate'], format='%Y%m%d', errors='coerce')
            
        return df
    
    def _extract_age(self, patient: dict) -> Optional[float]:
        """Extract and normalize patient age"""
        try:
            age_value = patient.get('patientonsetage')
            age_unit = patient.get('patientonsetageunit')
            
            if not age_value:
                return None
            
            age_value = float(age_value)
            
            # Convert to years
            if age_unit == '800':  # Decade
                return age_value * 10
            elif age_unit == '801':  # Year
                return age_value
            elif age_unit == '802':  # Month
                return age_value / 12
            elif age_unit == '803':  # Week
                return age_value / 52
            elif age_unit == '804':  # Day
                return age_value / 365
            
            return age_value
            
        except Exception:
            return None


if __name__ == '__main__':
    # Test the extractor
    extractor = FDAExtractor()
    data = extractor.extract_drug_events(
        start_date='2024-01-01',
        end_date='2024-01-01',
        limit=100
    )
    print(f"Extracted {len(data)} records")
    print(data.head())