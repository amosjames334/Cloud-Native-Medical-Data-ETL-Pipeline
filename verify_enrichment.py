
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.transformers.drug_transformer import DrugTransformer

def test_enrichment():
    print("Testing enrichment logic...")
    
    # Mock transformer (we only need the _enrich_data method)
    transformer = DrugTransformer('test-bucket')
    
    # Test case 1: Exact match
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
    
    if len(result) == 1 and result.iloc[0]['trial_count'] == 1:
        print("PASS: Exact match")
    else:
        print(f"FAIL: Exact match. Result: {result}")

    # Test case 2: Partial match
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
    
    if len(result) == 1 and result.iloc[0]['trial_count'] == 1:
        print("PASS: Partial match")
    else:
        print(f"FAIL: Partial match. Result: {result}")

if __name__ == "__main__":
    try:
        test_enrichment()
        print("Verification script finished.")
    except Exception as e:
        print(f"Verification failed with error: {e}")
