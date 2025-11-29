"""
Unit tests for data enrichment logic
"""

import pytest
import pandas as pd
from src.transformers.drug_transformer import DrugTransformer

class TestEnrichment:
    """Test data enrichment logic"""
    
    @pytest.fixture
    def transformer(self):
        return DrugTransformer('test-bucket')
    
    def test_enrichment_exact_match(self, transformer):
        """Test enrichment with exact string match"""
        fda_df = pd.DataFrame([
            {
                'drug_name_clean': 'DRUG A',
                'drug_indication': 'Headache',
                'safetyreportid': '1',
                'severity_score': 10,
                'seriousnessdeath': 0,
                'seriousnesshospitalization': 0
            }
        ])
        
        ct_df = pd.DataFrame([
            {
                'conditions_clean': 'HEADACHE',
                'nct_id': 'NCT1',
                'enrollment_count': 100,
                'is_completed': 1
            }
        ])
        
        result = transformer._enrich_data(fda_df, ct_df)
        
        assert len(result) == 1
        assert result.iloc[0]['trial_count'] == 1
        assert result.iloc[0]['total_enrollment'] == 100
    
    def test_enrichment_case_insensitive(self, transformer):
        """Test enrichment with case differences"""
        fda_df = pd.DataFrame([
            {
                'drug_name_clean': 'DRUG B',
                'drug_indication': 'Type 2 Diabetes',
                'safetyreportid': '2',
                'severity_score': 20,
                'seriousnessdeath': 0,
                'seriousnesshospitalization': 0
            }
        ])
        
        ct_df = pd.DataFrame([
            {
                'conditions_clean': 'TYPE 2 DIABETES',
                'nct_id': 'NCT2',
                'enrollment_count': 200,
                'is_completed': 0
            }
        ])
        
        result = transformer._enrich_data(fda_df, ct_df)
        
        assert len(result) == 1
        assert result.iloc[0]['trial_count'] == 1
    
    def test_enrichment_partial_match(self, transformer):
        """Test enrichment with partial string match"""
        fda_df = pd.DataFrame([
            {
                'drug_name_clean': 'DRUG C',
                'drug_indication': 'Lung Cancer',
                'safetyreportid': '3',
                'severity_score': 30,
                'seriousnessdeath': 1,
                'seriousnesshospitalization': 0
            }
        ])
        
        ct_df = pd.DataFrame([
            {
                'conditions_clean': 'NON-SMALL CELL LUNG CANCER',
                'nct_id': 'NCT3',
                'enrollment_count': 300,
                'is_completed': 1
            }
        ])
        
        result = transformer._enrich_data(fda_df, ct_df)
        
        assert len(result) == 1
        assert result.iloc[0]['trial_count'] == 1
    
    def test_enrichment_no_match(self, transformer):
        """Test enrichment with no match"""
        fda_df = pd.DataFrame([
            {
                'drug_name_clean': 'DRUG D',
                'drug_indication': 'Flu',
                'safetyreportid': '4',
                'severity_score': 5,
                'seriousnessdeath': 0,
                'seriousnesshospitalization': 0
            }
        ])
        
        ct_df = pd.DataFrame([
            {
                'conditions_clean': 'BROKEN LEG',
                'nct_id': 'NCT4',
                'enrollment_count': 50,
                'is_completed': 1
            }
        ])
        
        result = transformer._enrich_data(fda_df, ct_df)
        
        assert len(result) == 1
        assert result.iloc[0]['trial_count'] == 0
