"""
Drug Data Transformer
Transforms and enriches FDA and clinical trial data
"""

import pandas as pd
import argparse
from datetime import datetime
from src.loaders.s3_loader import S3Loader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DrugTransformer:
    """Transform and enrich medical data"""
    
    def __init__(self, s3_bucket: str):
        """
        Initialize transformer
        
        Args:
            s3_bucket: S3 bucket name
        """
        self.s3_loader = S3Loader(s3_bucket)
        self.bucket = s3_bucket
        
    def transform(self, date: str) -> dict:
        """
        Main transformation pipeline
        
        Args:
            date: Processing date in YYYY-MM-DD format
            
        Returns:
            Dictionary with transformation results
        """
        logger.info(f"Starting transformation for {date}")
        
        try:
            # Load raw data
            fda_data = self._load_fda_data(date)
            ct_data = self._load_clinical_trials_data(date)
            
            # Transform FDA data
            transformed_fda = self._transform_fda_data(fda_data)
            
            # Transform clinical trials data
            transformed_ct = self._transform_clinical_trials(ct_data)
            
            # Enrich and merge datasets
            enriched_data = self._enrich_data(transformed_fda, transformed_ct)
            
            # Save transformed data
            self._save_transformed_data(enriched_data, date)
            
            results = {
                'date': date,
                'fda_records': len(transformed_fda),
                'ct_records': len(transformed_ct),
                'enriched_records': len(enriched_data),
                'status': 'success'
            }
            
            logger.info(f"Transformation completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            raise
    
    def _load_fda_data(self, date: str) -> pd.DataFrame:
        """Load FDA raw data from S3"""
        year, month, day = date.split('-')
        s3_key = f"raw/fda/year={year}/month={month}/day={day}/data.json"
        
        logger.info(f"Loading FDA data from {s3_key}")
        data = self.s3_loader.read_json(s3_key)
        
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    def _load_clinical_trials_data(self, date: str) -> pd.DataFrame:
        """Load Clinical Trials raw data from S3"""
        year, month, day = date.split('-')
        s3_key = f"raw/clinical_trials/year={year}/month={month}/day={day}/data.json"
        
        logger.info(f"Loading Clinical Trials data from {s3_key}")
        data = self.s3_loader.read_json(s3_key)
        
        return pd.DataFrame(data) if data else pd.DataFrame()
    
    def _transform_fda_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform FDA adverse event data"""
        if df.empty:
            logger.warning("No FDA data to transform")
            return df
        
        logger.info(f"Transforming {len(df)} FDA records")
        
        # Create a copy
        transformed = df.copy()
        
        # Add processing metadata
        transformed['processed_date'] = datetime.now()
        transformed['data_source'] = 'FDA_OpenFDA'
        
        # Clean drug names
        if 'drug_name' in transformed.columns:
            transformed['drug_name_clean'] = transformed['drug_name'].str.upper().str.strip()
        
        # Create severity score
        transformed['severity_score'] = self._calculate_severity(transformed)
        
        # Categorize age groups
        if 'patient_age' in transformed.columns:
            transformed['age_group'] = pd.cut(
                transformed['patient_age'],
                bins=[0, 18, 30, 50, 65, 100],
                labels=['Pediatric', 'Young Adult', 'Adult', 'Senior', 'Elderly']
            )
        
        # Clean text fields
        text_fields = ['drug_indication', 'reaction']
        for field in text_fields:
            if field in transformed.columns:
                transformed[field] = transformed[field].fillna('').str.strip()
        
        # Add data quality flags
        transformed['is_complete'] = self._check_completeness(transformed)
        
        # Remove duplicates
        if 'safetyreportid' in transformed.columns:
            transformed = transformed.drop_duplicates(subset=['safetyreportid'], keep='first')
        
        logger.info(f"FDA transformation complete: {len(transformed)} records")
        return transformed
    
    def _transform_clinical_trials(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform clinical trials data"""
        if df.empty:
            logger.warning("No Clinical Trials data to transform")
            return df
        
        logger.info(f"Transforming {len(df)} Clinical Trials records")
        
        # Create a copy
        transformed = df.copy()
        
        # Add processing metadata
        transformed['processed_date'] = datetime.now()
        transformed['data_source'] = 'ClinicalTrials_gov'
        
        # Calculate study duration
        if 'start_date' in transformed.columns and 'completion_date' in transformed.columns:
            transformed['study_duration_days'] = (
                transformed['completion_date'] - transformed['start_date']
            ).dt.days
        
        # Parse phase information
        if 'phase' in transformed.columns:
            transformed['phase_numeric'] = transformed['phase'].apply(self._parse_phase)
        
        # Categorize study size
        if 'enrollment_count' in transformed.columns:
            transformed['study_size_category'] = pd.cut(
                transformed['enrollment_count'],
                bins=[0, 50, 200, 1000, float('inf')],
                labels=['Small', 'Medium', 'Large', 'Very Large']
            )
        
        # Create status flags
        if 'overall_status' in transformed.columns:
            transformed['is_active'] = transformed['overall_status'].isin([
                'RECRUITING', 'ACTIVE_NOT_RECRUITING', 'ENROLLING_BY_INVITATION'
            ])
            transformed['is_completed'] = transformed['overall_status'] == 'COMPLETED'
        
        # Clean condition names
        if 'conditions' in transformed.columns:
            transformed['conditions_clean'] = transformed['conditions'].str.upper()
        
        # Remove duplicates
        if 'nct_id' in transformed.columns:
            transformed = transformed.drop_duplicates(subset=['nct_id'], keep='first')
        
        logger.info(f"Clinical Trials transformation complete: {len(transformed)} records")
        return transformed
    
    def _enrich_data(self, fda_df: pd.DataFrame, ct_df: pd.DataFrame) -> pd.DataFrame:
        """Enrich and merge datasets"""
        logger.info("Enriching data")
        
        # Create enriched dataset
        enriched = pd.DataFrame()
        
        if not fda_df.empty:
            # Add FDA summary statistics
            fda_summary = fda_df.groupby('drug_name_clean').agg({
                'safetyreportid': 'count',
                'severity_score': 'mean',
                'seriousnessdeath': 'sum',
                'seriousnesshospitalization': 'sum'
            }).reset_index()
            
            fda_summary.columns = [
                'drug_name',
                'adverse_event_count',
                'avg_severity_score',
                'death_count',
                'hospitalization_count'
            ]
            
            enriched = fda_summary
        
        if not ct_df.empty:
            # Add clinical trials summary
            ct_summary = ct_df.groupby('conditions_clean').agg({
                'nct_id': 'count',
                'enrollment_count': 'sum',
                'is_completed': 'sum'
            }).reset_index()
            
            ct_summary.columns = [
                'condition',
                'trial_count',
                'total_enrollment',
                'completed_trials'
            ]
            
            # If we have both datasets, try to merge on condition/indication
            if not enriched.empty and 'drug_indication' in fda_df.columns:
                # Create mapping between drugs and conditions
                # Get unique indications for each drug
                drug_indications = fda_df[['drug_name_clean', 'drug_indication']].drop_duplicates()
                
                # Normalize strings for matching
                def normalize(text):
                    if not isinstance(text, str):
                        return ""
                    return text.lower().strip().replace(' ', '')
                
                drug_indications['indication_norm'] = drug_indications['drug_indication'].apply(normalize)
                ct_summary['condition_norm'] = ct_summary['condition'].apply(normalize)
                
                # Merge logic
                merged_data = []
                
                for _, drug_row in enriched.iterrows():
                    drug_name = drug_row['drug_name']
                    
                    # Find indications for this drug
                    indications = drug_indications[
                        drug_indications['drug_name_clean'] == drug_name
                    ]['indication_norm'].tolist()
                    
                    # Find matching trials
                    matches = ct_summary[
                        ct_summary['condition_norm'].apply(
                            lambda x: any(ind in x or x in ind for ind in indications if ind)
                        )
                    ]
                    
                    if not matches.empty:
                        # Aggregate trial data
                        trial_stats = {
                            'trial_count': matches['trial_count'].sum(),
                            'total_enrollment': matches['total_enrollment'].sum(),
                            'completed_trials': matches['completed_trials'].sum()
                        }
                    else:
                        trial_stats = {
                            'trial_count': 0,
                            'total_enrollment': 0,
                            'completed_trials': 0
                        }
                        
                    # Combine data
                    row_data = drug_row.to_dict()
                    row_data.update(trial_stats)
                    merged_data.append(row_data)
                
                enriched = pd.DataFrame(merged_data)
                
            elif enriched.empty:
                enriched = ct_summary
        
        logger.info(f"Data enrichment complete: {len(enriched)} records")
        return enriched
    
    def _save_transformed_data(self, df: pd.DataFrame, date: str):
        """Save transformed data to S3"""
        if df.empty:
            logger.warning("No data to save")
            return
        
        year, month, day = date.split('-')
        
        # Save as parquet (efficient columnar format)
        s3_key = f"processed/year={year}/month={month}/day={day}/enriched_data.parquet"
        
        logger.info(f"Saving transformed data to {s3_key}")
        self.s3_loader.write_parquet(df, s3_key)
        
        # Also save summary as CSV for easy viewing
        summary_key = f"processed/year={year}/month={month}/day={day}/summary.csv"
        self.s3_loader.write_csv(df.head(1000), summary_key)  # First 1000 rows
        
        logger.info("Data saved successfully")
    
    def _calculate_severity(self, df: pd.DataFrame) -> pd.Series:
        """Calculate severity score from FDA data"""
        score = pd.Series(0, index=df.index)
        
        if 'serious' in df.columns:
            score += df['serious'].fillna(0) * 2
        if 'seriousnessdeath' in df.columns:
            score += df['seriousnessdeath'].fillna(0) * 10
        if 'seriousnesshospitalization' in df.columns:
            score += df['seriousnesshospitalization'].fillna(0) * 5
        
        return score
    
    def _check_completeness(self, df: pd.DataFrame) -> pd.Series:
        """Check record completeness"""
        required_fields = ['safetyreportid', 'drug_name', 'receivedate']
        
        completeness = pd.Series(True, index=df.index)
        for field in required_fields:
            if field in df.columns:
                completeness &= df[field].notna()
        
        return completeness
    
    def _parse_phase(self, phase_str: str) -> float:
        """Parse phase string to numeric value"""
        if pd.isna(phase_str) or not phase_str:
            return 0.0
        
        phase_str = str(phase_str).upper()
        
        if 'PHASE 4' in phase_str or 'PHASE IV' in phase_str:
            return 4.0
        elif 'PHASE 3' in phase_str or 'PHASE III' in phase_str:
            return 3.0
        elif 'PHASE 2' in phase_str or 'PHASE II' in phase_str:
            return 2.0
        elif 'EARLY' in phase_str:
            return 0.5
        elif 'PHASE 1' in phase_str or 'PHASE I' in phase_str:
            return 1.0
        
        return 0.0


def main():
    """Main entry point for transformer"""
    parser = argparse.ArgumentParser(description='Transform medical data')
    parser.add_argument('--date', required=True, help='Processing date (YYYY-MM-DD)')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    
    args = parser.parse_args()
    
    transformer = DrugTransformer(args.bucket)
    results = transformer.transform(args.date)
    
    print(f"Transformation completed: {results}")


if __name__ == '__main__':
    main()