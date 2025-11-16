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
        assert extractor.BASE_URL == "https://api.fda.gov/drug/event.json"
    
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
                    'safetyreportid': '123456',
                    'receivedate': '20240101',
                    'serious': 1,
                    'patient': {
                        'patientsex': '1',
                        'drug': [{'medicinalproduct': 'ASPIRIN'}],
                        'reaction': [{'reactionmeddrapt': 'HEADACHE'}]
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test extraction
        extractor = FDAExtractor()
        result = extractor.extract_drug_events(
            start_date='2024-01-01',
            end_date='2024-01-01',
            limit=10
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'safetyreportid' in result.columns
    
    @patch('src.extractors.fda_extractor.requests.Session.get')
    def test_extract_empty_results(self, mock_get):
        """Test extraction with no results"""
        mock_response = Mock()
        mock_response.json.return_value = {'results': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        extractor = FDAExtractor()
        result = extractor.extract_drug_events(
            start_date='2024-01-01',
            end_date='2024-01-01',
            limit=10
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_extract_age_conversion(self):
        """Test age extraction and conversion"""
        extractor = FDAExtractor()
        
        # Test year conversion
        patient = {'patientonsetage': '50', 'patientonsetageunit': '801'}
        age = extractor._extract_age(patient)
        assert age == 50.0
        
        # Test month conversion
        patient = {'patientonsetage': '24', 'patientonsetageunit': '802'}
        age = extractor._extract_age(patient)
        assert age == pytest.approx(2.0, rel=0.1)
        
        # Test decade conversion
        patient = {'patientonsetage': '5', 'patientonsetageunit': '800'}
        age = extractor._extract_age(patient)
        assert age == 50.0
    
    def test_parse_records_with_invalid_data(self):
        """Test parsing with invalid/missing data"""
        extractor = FDAExtractor()
        
        records = [
            {'safetyreportid': '123'},  # Minimal data
            {},  # Empty record
            {'safetyreportid': '456', 'receivedate': '20240101'}
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