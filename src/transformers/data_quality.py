"""
Data Quality Checker
Validates transformed data against quality rules
"""

import pandas as pd
from typing import Dict, List
from src.loaders.s3_loader import S3Loader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataQualityChecker:
    """Validate data quality for medical ETL pipeline"""
    
    def __init__(self, s3_bucket: str):
        """
        Initialize data quality checker
        
        Args:
            s3_bucket: S3 bucket name
        """
        self.s3_loader = S3Loader(s3_bucket)
        self.bucket = s3_bucket
        
    def validate_transformed_data(self, date: str) -> Dict:
        """
        Run all quality checks on transformed data
        
        Args:
            date: Processing date (YYYY-MM-DD)
            
        Returns:
            Dictionary with validation results
        """
        logger.info(f"Starting data quality checks for {date}")
        
        try:
            # Load transformed data
            df = self._load_transformed_data(date)
            
            if df.empty:
                return {
                    'passed': False,
                    'message': 'No data found',
                    'failures': ['No data to validate']
                }
            
            # Run all checks
            checks = [
                self._check_completeness(df),
                self._check_data_types(df),
                self._check_value_ranges(df),
                self._check_duplicates(df),
                self._check_record_count(df),
                self._check_date_consistency(df)
            ]
            
            # Aggregate results
            failures = []
            for check in checks:
                if not check['passed']:
                    failures.extend(check['failures'])
            
            passed = len(failures) == 0
            
            results = {
                'date': date,
                'passed': passed,
                'total_checks': len(checks),
                'failed_checks': len(failures),
                'failures': failures,
                'record_count': len(df)
            }
            
            if passed:
                logger.info(f"All quality checks passed for {date}")
            else:
                logger.warning(f"Quality checks failed: {failures}")
            
            return results
            
        except Exception as e:
            logger.error(f"Quality check error: {e}")
            return {
                'passed': False,
                'message': str(e),
                'failures': [str(e)]
            }
    
    def _load_transformed_data(self, date: str) -> pd.DataFrame:
        """Load transformed data from S3"""
        year, month, day = date.split('-')
        s3_key = f"processed/year={year}/month={month}/day={day}/enriched_data.parquet"
        
        logger.info(f"Loading data from {s3_key}")
        return self.s3_loader.read_parquet(s3_key)
    
    def _check_completeness(self, df: pd.DataFrame) -> Dict:
        """Check for missing critical fields"""
        logger.info("Checking data completeness")
        
        failures = []
        
        # Define required columns based on data source
        if 'data_source' in df.columns:
            if (df['data_source'] == 'FDA_OpenFDA').any():
                required_fda = ['safetyreportid', 'receivedate', 'drug_name']
                fda_df = df[df['data_source'] == 'FDA_OpenFDA']
                
                for col in required_fda:
                    if col not in fda_df.columns:
                        failures.append(f"Missing required FDA column: {col}")
                    elif fda_df[col].isna().sum() > 0:
                        null_pct = (fda_df[col].isna().sum() / len(fda_df)) * 100
                        if null_pct > 10:  # More than 10% missing
                            failures.append(
                                f"FDA column {col} has {null_pct:.1f}% missing values"
                            )
            
            if (df['data_source'] == 'ClinicalTrials_gov').any():
                required_ct = ['nct_id', 'brief_title', 'overall_status']
                ct_df = df[df['data_source'] == 'ClinicalTrials_gov']
                
                for col in required_ct:
                    if col not in ct_df.columns:
                        failures.append(f"Missing required CT column: {col}")
                    elif ct_df[col].isna().sum() > 0:
                        null_pct = (ct_df[col].isna().sum() / len(ct_df)) * 100
                        if null_pct > 10:
                            failures.append(
                                f"CT column {col} has {null_pct:.1f}% missing values"
                            )
        
        return {
            'check': 'completeness',
            'passed': len(failures) == 0,
            'failures': failures
        }
    
    def _check_data_types(self, df: pd.DataFrame) -> Dict:
        """Validate data types"""
        logger.info("Checking data types")
        
        failures = []
        
        # Check numeric columns
        numeric_cols = ['severity_score', 'adverse_event_count', 'enrollment_count']
        for col in numeric_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    failures.append(f"Column {col} should be numeric")
        
        # Check date columns
        date_cols = ['receivedate', 'processed_date', 'start_date', 'completion_date']
        for col in date_cols:
            if col in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df[col]):
                    failures.append(f"Column {col} should be datetime")
        
        return {
            'check': 'data_types',
            'passed': len(failures) == 0,
            'failures': failures
        }
    
    def _check_value_ranges(self, df: pd.DataFrame) -> Dict:
        """Check if values are within acceptable ranges"""
        logger.info("Checking value ranges")
        
        failures = []
        
        # Check severity score
        if 'severity_score' in df.columns:
            invalid = df[(df['severity_score'] < 0) | (df['severity_score'] > 100)]
            if len(invalid) > 0:
                failures.append(
                    f"Found {len(invalid)} records with invalid severity_score"
                )
        
        # Check patient age
        if 'patient_age' in df.columns:
            invalid = df[(df['patient_age'] < 0) | (df['patient_age'] > 120)]
            if len(invalid) > 0:
                failures.append(
                    f"Found {len(invalid)} records with invalid patient_age"
                )
        
        # Check enrollment count
        if 'enrollment_count' in df.columns:
            invalid = df[df['enrollment_count'] < 0]
            if len(invalid) > 0:
                failures.append(
                    f"Found {len(invalid)} records with negative enrollment_count"
                )
        
        return {
            'check': 'value_ranges',
            'passed': len(failures) == 0,
            'failures': failures
        }
    
    def _check_duplicates(self, df: pd.DataFrame) -> Dict:
        """Check for duplicate records"""
        logger.info("Checking for duplicates")
        
        failures = []
        
        # Check for duplicates based on primary keys
        if 'safetyreportid' in df.columns:
            fda_df = df[df['data_source'] == 'FDA_OpenFDA'] if 'data_source' in df.columns else df
            duplicates = fda_df[fda_df.duplicated(subset=['safetyreportid'], keep=False)]
            if len(duplicates) > 0:
                failures.append(
                    f"Found {len(duplicates)} duplicate FDA safety reports"
                )
        
        if 'nct_id' in df.columns:
            ct_df = df[df['data_source'] == 'ClinicalTrials_gov'] if 'data_source' in df.columns else df
            duplicates = ct_df[ct_df.duplicated(subset=['nct_id'], keep=False)]
            if len(duplicates) > 0:
                failures.append(
                    f"Found {len(duplicates)} duplicate clinical trial records"
                )
        
        return {
            'check': 'duplicates',
            'passed': len(failures) == 0,
            'failures': failures
        }
    
    def _check_record_count(self, df: pd.DataFrame) -> Dict:
        """Check if record count is reasonable"""
        logger.info("Checking record count")
        
        failures = []
        
        # Minimum threshold
        min_records = 10
        if len(df) < min_records:
            failures.append(
                f"Record count ({len(df)}) is below minimum threshold ({min_records})"
            )
        
        # Check by data source
        if 'data_source' in df.columns:
            source_counts = df['data_source'].value_counts()
            
            for source, count in source_counts.items():
                if count < 5:
                    failures.append(
                        f"Data source {source} has only {count} records"
                    )
        
        return {
            'check': 'record_count',
            'passed': len(failures) == 0,
            'failures': failures
        }
    
    def _check_date_consistency(self, df: pd.DataFrame) -> Dict:
        """Check date field consistency"""
        logger.info("Checking date consistency")
        
        failures = []
        
        # Check that start_date is before completion_date
        if 'start_date' in df.columns and 'completion_date' in df.columns:
            invalid = df[
                (df['start_date'].notna()) &
                (df['completion_date'].notna()) &
                (df['start_date'] > df['completion_date'])
            ]
            if len(invalid) > 0:
                failures.append(
                    f"Found {len(invalid)} records where start_date > completion_date"
                )
        
        # Check that dates are not in the future
        now = pd.Timestamp.now()
        date_cols = ['receivedate', 'start_date', 'completion_date']
        
        for col in date_cols:
            if col in df.columns:
                future = df[df[col] > now]
                if len(future) > 0:
                    failures.append(
                        f"Found {len(future)} records with future {col}"
                    )
        
        return {
            'check': 'date_consistency',
            'passed': len(failures) == 0,
            'failures': failures
        }


def main():
    """Main entry point for quality checker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check data quality')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--date', required=True, help='Processing date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    checker = DataQualityChecker(args.bucket)
    results = checker.validate_transformed_data(args.date)
    
    print(f"\nData Quality Check Results:")
    print(f"Date: {results.get('date')}")
    print(f"Passed: {results['passed']}")
    print(f"Record Count: {results.get('record_count')}")
    
    if not results['passed']:
        print(f"\nFailures ({len(results['failures'])}):")
        for failure in results['failures']:
            print(f"  - {failure}")
    
    exit(0 if results['passed'] else 1)


if __name__ == '__main__':
    main()