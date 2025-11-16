"""
Unit tests for data transformers
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from src.transformers.drug_transformer import DrugTransformer


class TestDrugTransformer:
    """Test drug data transformer"""
    
    @pytest.fixture
    def sample_fda_data(self):
        """Sample FDA data for testing"""
        return pd.DataFrame([
            {
                'safetyreportid': '123',
                'receivedate': '2024-01-01',
                'serious': 1,
                'seriousnessdeath': 0,
                'seriousnesshospitalization': 1,
                'drug_name': 'ASPIRIN',
                'drug_indication': 'PAIN',
                'reaction': 'HEADACHE',
                'patient_age': 45,
                'patient_sex': '1'
            },
            {
                'safetyreportid': '124',
                'receivedate': '2024-01-01',
                'serious': 0,
                'seriousnessdeath': 0,
                'seriousnesshospitalization': 0,
                'drug_name': 'IBUPROFEN',
                'drug_indication': 'FEVER',
                'reaction': 'NAUSEA',
                'patient_age': 32,
                'patient_sex': '2'
            }
        ])
    
    @pytest.fixture
    def sample_ct_data(self):
        """Sample clinical trials data for testing"""
        return pd.DataFrame([
            {
                'nct_id': 'NCT12345678',
                'brief_title': 'Test Study',
                'overall_status': 'RECRUITING',
                'phase': 'PHASE 3',
                'enrollment_count': 150,
                'conditions': 'DIABETES',
                'start_date': pd.Timestamp('2023-01-01'),
                'completion_date': pd.Timestamp('2024-12-31')
            }
        ])
    
    def test_transformer_initialization(self):
        """Test transformer can be initialized"""
        transformer = DrugTransformer('test-bucket')
        assert transformer is not None
        assert transformer.bucket == 'test-bucket'
    
    def test_transform_fda_data(self, sample_fda_data):
        """Test FDA data transformation"""
        transformer = DrugTransformer('test-bucket')
        result = transformer._transform_fda_data(sample_fda_data)
        
        # Check new columns are added
        assert 'processed_date' in result.columns
        assert 'data_source' in result.columns
        assert 'severity_score' in result.columns
        assert 'age_group' in result.columns
        assert 'is_complete' in result.columns
        
        # Check data source is set correctly
        assert all(result['data_source'] == 'FDA_OpenFDA')
        
        # Check drug names are cleaned
        assert 'drug_name_clean' in result.columns
        assert all(result['drug_name_clean'].str.isupper())
    
    def test_transform_empty_fda_data(self):
        """Test transformation with empty FDA data"""
        transformer = DrugTransformer('test-bucket')
        empty_df = pd.DataFrame()
        
        result = transformer._transform_fda_data(empty_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_calculate_severity(self, sample_fda_data):
        """Test severity score calculation"""
        transformer = DrugTransformer('test-bucket')
        scores = transformer._calculate_severity(sample_fda_data)
        
        # First record: serious=1, death=0, hospitalization=1
        # Score should be: 1*2 + 0*10 + 1*5 = 7
        assert scores.iloc[0] == 7
        
        # Second record: all zeros
        assert scores.iloc[1] == 0
    
    def test_check_completeness(self, sample_fda_data):
        """Test completeness check"""
        transformer = DrugTransformer('test-bucket')
        completeness = transformer._check_completeness(sample_fda_data)
        
        # All sample records have required fields
        assert all(completeness)
        
        # Test with missing data
        incomplete_data = sample_fda_data.copy()
        incomplete_data.loc[0, 'safetyreportid'] = None
        completeness = transformer._check_completeness(incomplete_data)
        assert not completeness.iloc[0]
        assert completeness.iloc[1]
    
    def test_transform_clinical_trials(self, sample_ct_data):
        """Test clinical trials data transformation"""
        transformer = DrugTransformer('test-bucket')
        result = transformer._transform_clinical_trials(sample_ct_data)
        
        # Check new columns
        assert 'processed_date' in result.columns
        assert 'data_source' in result.columns
        assert 'study_duration_days' in result.columns
        assert 'phase_numeric' in result.columns
        assert 'study_size_category' in result.columns
        assert 'is_active' in result.columns
        assert 'is_completed' in result.columns
        
        # Check data source
        assert all(result['data_source'] == 'ClinicalTrials_gov')
        
        # Check study duration calculation
        assert result['study_duration_days'].iloc[0] > 0
    
    def test_parse_phase(self):
        """Test phase parsing"""
        transformer = DrugTransformer('test-bucket')
        
        assert transformer._parse_phase('PHASE 1') == 1.0
        assert transformer._parse_phase('PHASE 2') == 2.0
        assert transformer._parse_phase('PHASE 3') == 3.0
        assert transformer._parse_phase('PHASE 4') == 4.0
        assert transformer._parse_phase('EARLY PHASE 1') == 0.5
        assert transformer._parse_phase('') == 0.0
        assert transformer._parse_phase(None) == 0.0
    
    def test_enrich_data(self, sample_fda_data, sample_ct_data):
        """Test data enrichment"""
        transformer = DrugTransformer('test-bucket')
        
        # Transform data first
        transformed_fda = transformer._transform_fda_data(sample_fda_data)
        transformed_ct = transformer._transform_clinical_trials(sample_ct_data)
        
        # Enrich
        result = transformer._enrich_data(transformed_fda, transformed_ct)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
    
    def test_enrich_data_fda_only(self, sample_fda_data):
        """Test enrichment with only FDA data"""
        transformer = DrugTransformer('test-bucket')
        transformed_fda = transformer._transform_fda_data(sample_fda_data)
        
        result = transformer._enrich_data(transformed_fda, pd.DataFrame())
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'adverse_event_count' in result.columns
    
    def test_enrich_data_ct_only(self, sample_ct_data):
        """Test enrichment with only clinical trials data"""
        transformer = DrugTransformer('test-bucket')
        transformed_ct = transformer._transform_clinical_trials(sample_ct_data)
        
        result = transformer._enrich_data(pd.DataFrame(), transformed_ct)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'trial_count' in result.columns


if __name__ == '__main__':
    pytest.main([__file__, '-v'])