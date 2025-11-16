"""
ClinicalTrials.gov Data Extractor
Extracts clinical trial data from ClinicalTrials.gov API v2
"""

import requests
import pandas as pd
from typing import Optional, List
import time
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ClinicalTrialsExtractor:
    """Extract data from ClinicalTrials.gov API v2"""
    
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
    
    def __init__(self):
        """Initialize ClinicalTrials extractor"""
        self.session = requests.Session()
        
    def extract_studies(
        self,
        last_update_date: str,
        page_size: int = 100,
        max_studies: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Extract clinical trial studies
        
        Args:
            last_update_date: Filter studies updated after this date (YYYY-MM-DD)
            page_size: Number of studies per page (max 1000)
            max_studies: Maximum number of studies to fetch
            
        Returns:
            DataFrame with clinical trial data
        """
        logger.info(f"Extracting Clinical Trials data updated after {last_update_date}")
        
        all_studies = []
        page_token = None
        
        while True:
            try:
                studies, next_token = self._fetch_page(
                    last_update_date=last_update_date,
                    page_size=page_size,
                    page_token=page_token
                )
                
                all_studies.extend(studies)
                logger.info(f"Fetched {len(studies)} studies (total: {len(all_studies)})")
                
                # Check stopping conditions
                if not next_token:
                    break
                if max_studies and len(all_studies) >= max_studies:
                    all_studies = all_studies[:max_studies]
                    break
                    
                page_token = next_token
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error fetching studies: {e}")
                break
        
        # Convert to DataFrame
        df = self._parse_studies(all_studies)
        logger.info(f"Extracted {len(df)} clinical trial records")
        
        return df
    
    def _fetch_page(
        self,
        last_update_date: str,
        page_size: int,
        page_token: Optional[str] = None
    ) -> tuple:
        """Fetch a single page of results"""
        
        params = {
            'filter.advanced': f'AREA[LastUpdatePostDate]RANGE[{last_update_date},MAX]',
            'pageSize': min(page_size, 1000),
            'format': 'json'
        }
        
        if page_token:
            params['pageToken'] = page_token
        
        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            studies = data.get('studies', [])
            next_token = data.get('nextPageToken')
            
            return studies, next_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def _parse_studies(self, studies: List[dict]) -> pd.DataFrame:
        """Parse clinical trial studies into structured DataFrame"""
        parsed_data = []
        
        for study in studies:
            try:
                protocol = study.get('protocolSection', {})
                
                # Identification
                id_module = protocol.get('identificationModule', {})
                
                # Status
                status_module = protocol.get('statusModule', {})
                
                # Description
                desc_module = protocol.get('descriptionModule', {})
                
                # Conditions
                conditions_module = protocol.get('conditionsModule', {})
                
                # Design
                design_module = protocol.get('designModule', {})
                
                # Arms/Interventions
                arms_module = protocol.get('armsInterventionsModule', {})
                
                # Outcomes
                outcomes_module = protocol.get('outcomesModule', {})
                
                # Eligibility
                eligibility_module = protocol.get('eligibilityModule', {})
                
                # Contacts
                contacts_module = protocol.get('contactsLocationsModule', {})
                
                parsed = {
                    # Identification
                    'nct_id': id_module.get('nctId'),
                    'org_study_id': id_module.get('orgStudyIdInfo', {}).get('id'),
                    'brief_title': id_module.get('briefTitle'),
                    'official_title': id_module.get('officialTitle'),
                    
                    # Status
                    'overall_status': status_module.get('overallStatus'),
                    'study_first_post_date': status_module.get('studyFirstPostDateStruct', {}).get('date'),
                    'last_update_post_date': status_module.get('lastUpdatePostDateStruct', {}).get('date'),
                    'start_date': status_module.get('startDateStruct', {}).get('date'),
                    'completion_date': status_module.get('completionDateStruct', {}).get('date'),
                    
                    # Description
                    'brief_summary': desc_module.get('briefSummary'),
                    'detailed_description': desc_module.get('detailedDescription'),
                    
                    # Conditions
                    'conditions': ', '.join(conditions_module.get('conditions', [])),
                    'keywords': ', '.join(conditions_module.get('keywords', [])),
                    
                    # Design
                    'study_type': design_module.get('studyType'),
                    'phase': ', '.join(design_module.get('phases', [])),
                    'enrollment_count': design_module.get('enrollmentInfo', {}).get('count'),
                    'allocation': design_module.get('designInfo', {}).get('allocation'),
                    'intervention_model': design_module.get('designInfo', {}).get('interventionModel'),
                    'primary_purpose': design_module.get('designInfo', {}).get('primaryPurpose'),
                    'masking': design_module.get('designInfo', {}).get('masking', {}).get('masking'),
                    
                    # Interventions
                    'intervention_types': self._extract_interventions(arms_module),
                    
                    # Outcomes
                    'primary_outcome_measures': self._extract_outcomes(
                        outcomes_module.get('primaryOutcomes', [])
                    ),
                    
                    # Eligibility
                    'gender': eligibility_module.get('sex'),
                    'min_age': eligibility_module.get('minimumAge'),
                    'max_age': eligibility_module.get('maximumAge'),
                    'accepts_healthy': eligibility_module.get('healthyVolunteers'),
                    
                    # Location
                    'location_countries': ', '.join(
                        [loc.get('country', '') for loc in contacts_module.get('locations', [])]
                    ),
                    
                    # Sponsor
                    'lead_sponsor': protocol.get('sponsorCollaboratorsModule', {})
                        .get('leadSponsor', {}).get('name'),
                }
                
                parsed_data.append(parsed)
                
            except Exception as e:
                logger.warning(f"Error parsing study {study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')}: {e}")
                continue
        
        df = pd.DataFrame(parsed_data)
        
        # Data type conversions
        if not df.empty:
            date_columns = ['study_first_post_date', 'last_update_post_date', 'start_date', 'completion_date']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            if 'enrollment_count' in df.columns:
                df['enrollment_count'] = pd.to_numeric(df['enrollment_count'], errors='coerce')
        
        return df
    
    def _extract_interventions(self, arms_module: dict) -> str:
        """Extract intervention types"""
        try:
            interventions = arms_module.get('interventions', [])
            types = [i.get('type', '') for i in interventions]
            return ', '.join(set(filter(None, types)))
        except Exception:
            return ''
    
    def _extract_outcomes(self, outcomes: List[dict]) -> str:
        """Extract outcome measures"""
        try:
            measures = [o.get('measure', '') for o in outcomes[:3]]  # Top 3
            return ' | '.join(filter(None, measures))
        except Exception:
            return ''


if __name__ == '__main__':
    # Test the extractor
    extractor = ClinicalTrialsExtractor()
    data = extractor.extract_studies(
        last_update_date='2024-01-01',
        page_size=50,
        max_studies=100
    )
    print(f"Extracted {len(data)} records")
    print(data.head())
    print("\nColumns:", data.columns.tolist())