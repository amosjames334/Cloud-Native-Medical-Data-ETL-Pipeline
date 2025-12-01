"""
Unit tests for data extractors
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from src.extractors.fda_extractor import FDAExtractor
from src.extractors.clinicaltrials_extractor import ClinicalTrialsExtractor


class TestFDAExtractor:
    """Test FDA data extractor"""
    
    def test_extractor_initialization(self):
        """Test extractor can be initialized"""
        extractor = FDAExtractor()
        assert extractor is not None
        assert extractor.BASE_URL == "https://api.fda.gov/drug/drugsfda.json"
    
    def test_extractor_with_api_key(self):
        """Test extractor initialization with API key"""
        api_key = "test_key_123"
        extractor = FDAExtractor(api_key=api_key)
        assert extractor.api_key == api_key
    
    @patch('src.extractors.fda_extractor.requests.Session.get')
    def test_extract_drug_events_success(self, mock_get):
        """Test successful data extraction"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'results': [
                {
                    'application_number': 'NDA123456',
                    'sponsor_name': 'TEST PHARMA',
                    'products': [
                        {
                            'brand_name': 'TEST DRUG',
                            'active_ingredients': [{'name': 'TEST INGREDIENT'}],
                            'marketing_status': 'Prescription'
                        }
                    ],
                    'submissions': [
                        {
                            'submission_status_date': '20250115',
                            'submission_type': 'ORIGINAL'
                        }
                    ]
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test extraction
        extractor = FDAExtractor()
        result = extractor.extract_drug_events(
            start_date='2025-01-01',
            end_date='2025-01-30',
            limit=10
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'application_number' in result.columns
        assert 'brand_name' in result.columns
    
    @patch('src.extractors.fda_extractor.requests.Session.get')
    def test_extract_empty_results(self, mock_get):
        """Test extraction with no results"""
        mock_response = Mock()
        mock_response.json.return_value = {'results': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        extractor = FDAExtractor()
        result = extractor.extract_drug_events(
            start_date='2025-01-01',
            end_date='2025-01-30',
            limit=10
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_parse_records_with_invalid_data(self):
        """Test parsing with invalid/missing data"""
        extractor = FDAExtractor()
        
        records = [
            {'application_number': '123'},  # Minimal data
            {},  # Empty record
            {'application_number': '456', 'submissions': []}
        ]
        
        result = extractor._parse_records(records)
        assert isinstance(result, pd.DataFrame)
        # Should handle invalid records gracefully


class TestClinicalTrialsExtractor:
    """Test ClinicalTrials.gov data extractor"""
    
    def test_extractor_initialization(self):
        """Test extractor can be initialized"""
        extractor = ClinicalTrialsExtractor()
        assert extractor is not None
        assert extractor.BASE_URL == "https://clinicaltrials.gov/api/v2/studies"
    
    @patch('src.extractors.clinicaltrials_extractor.requests.Session.get')
    def test_extract_studies_success(self, mock_get):
        """Test successful study extraction"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'studies': [
                {
                    'protocolSection': {
                        'identificationModule': {
                            'nctId': 'NCT12345678',
                            'briefTitle': 'Test Study'
                        },
                        'statusModule': {
                            'overallStatus': 'RECRUITING'
                        }
                    }
                }
            ],
            'nextPageToken': None
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        extractor = ClinicalTrialsExtractor()
        result = extractor.extract_studies(
            last_update_date='2024-01-01',
            page_size=10
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'nct_id' in result.columns
    
    @patch('src.extractors.clinicaltrials_extractor.requests.Session.get')
    def test_extract_empty_studies(self, mock_get):
        """Test extraction with no studies"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'studies': [],
            'nextPageToken': None
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        extractor = ClinicalTrialsExtractor()
        result = extractor.extract_studies(
            last_update_date='2024-01-01',
            page_size=10
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_extract_interventions(self):
        """Test intervention extraction"""
        extractor = ClinicalTrialsExtractor()
        
        arms_module = {
            'interventions': [
                {'type': 'Drug'},
                {'type': 'Device'},
                {'type': 'Drug'}  # Duplicate
            ]
        }
        
        result = extractor._extract_interventions(arms_module)
        assert 'Drug' in result
        assert 'Device' in result
    
    def test_extract_outcomes(self):
        """Test outcome measure extraction"""
        extractor = ClinicalTrialsExtractor()
        
        outcomes = [
            {'measure': 'Primary Outcome 1'},
            {'measure': 'Primary Outcome 2'},
            {'measure': 'Primary Outcome 3'},
            {'measure': 'Primary Outcome 4'}  # Should be excluded (max 3)
        ]
        
        result = extractor._extract_outcomes(outcomes)
        assert 'Primary Outcome 1' in result
        assert 'Primary Outcome 4' not in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])