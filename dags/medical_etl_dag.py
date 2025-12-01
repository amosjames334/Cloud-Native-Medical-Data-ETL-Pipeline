"""
Medical ETL Pipeline DAG
Orchestrates extraction, transformation, and loading of FDA and clinical trial data
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
import yaml
import os
import sys

# Add repo root to sys.path to allow importing from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), 'config', 'pipeline_config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Default arguments
default_args = {
    'owner': 'Amos Jaimes',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
}

# Environment variables
S3_BUCKET = os.getenv('S3_BUCKET', 'medical-etl-data-amos1234')
DOCKER_IMAGE = os.getenv('DOCKER_IMAGE', 'medical-etl-transform:v1')
AWS_CONN_ID = 'aws_default'


def extract_fda_data(**context):
    """Extract FDA drug event data"""
    from src.extractors.fda_extractor import FDAExtractor
    
    execution_date = context['ds']
    extractor = FDAExtractor()
    
    # Extract data
    data = extractor.extract_drug_events(
        start_date=execution_date,
        end_date=execution_date,
        limit=config['extraction']['fda_limit']
    )
    
    # Save raw data to S3
    #s3_hook = S3Hook(aws_conn_id=AWS_CONN_ID)
    #s3_key = f"raw/fda/year={execution_date[:4]}/month={execution_date[5:7]}/day={execution_date[8:10]}/data.json"
    
    #s3_hook.load_string(
    #    string_data=data.to_json(orient='records'),
    #    key=s3_key,
    #    bucket_name=S3_BUCKET,
    #    replace=True
    #)
    
    context['task_instance'].xcom_push(key='fda_s3_key', value= "abederf")
    context['task_instance'].xcom_push(key='fda_record_count', value= 29)
    
    return s3_key


def extract_clinical_trials(**context):
    """Extract clinical trials data"""
    from src.extractors.clinicaltrials_extractor import ClinicalTrialsExtractor
    
    execution_date = context['ds']
    extractor = ClinicalTrialsExtractor()
    
    # Extract data
    data = extractor.extract_studies(
        last_update_date=execution_date,
        page_size=config['extraction']['clinical_trials_limit']
    )
    
    # Save raw data to S3
    s3_hook = S3Hook(aws_conn_id=AWS_CONN_ID)
    s3_key = f"raw/clinical_trials/year={execution_date[:4]}/month={execution_date[5:7]}/day={execution_date[8:10]}/data.json"
    
    s3_hook.load_string(
        string_data=data.to_json(orient='records'),
        key=s3_key,
        bucket_name=S3_BUCKET,
        replace=True
    )
    
    context['task_instance'].xcom_push(key='ct_s3_key', value=s3_key)
    context['task_instance'].xcom_push(key='ct_record_count', value=len(data))
    
    return s3_key


def validate_extraction(**context):
    """Validate extracted data"""
    ti = context['task_instance']
    fda_count = ti.xcom_pull(task_ids='extract_fda_data', key='fda_record_count')
    ct_count = ti.xcom_pull(task_ids='extract_clinical_trials', key='ct_record_count')
    
    if fda_count == 0:
        raise ValueError("No FDA records extracted!")
    if ct_count == 0:
        raise ValueError("No Clinical Trials records extracted!")
    
    print(f"Validation passed: FDA={fda_count}, Clinical Trials={ct_count}")
    return True


def quality_check(**context):
    """Run data quality checks"""
    from src.transformers.data_quality import DataQualityChecker
    
    execution_date = context['ds']
    checker = DataQualityChecker(S3_BUCKET)
    
    # Check transformed data
    results = checker.validate_transformed_data(execution_date)
    
    if not results['passed']:
        raise ValueError(f"Data quality check failed: {results['failures']}")
    
    print(f"Quality check passed: {results}")
    return results


def send_completion_notification(**context):
    """Send completion notification"""
    ti = context['task_instance']
    execution_date = context['ds']
    
    fda_count = ti.xcom_pull(task_ids='extract_fda_data', key='fda_record_count')
    ct_count = ti.xcom_pull(task_ids='extract_clinical_trials', key='ct_record_count')
    
    message = f"""
    Medical ETL Pipeline Completed Successfully
    
    Date: {execution_date}
    FDA Records: {fda_count}
    Clinical Trials: {ct_count}
    S3 Bucket: {S3_BUCKET}
    
    Data available at:
    s3://{S3_BUCKET}/processed/year={execution_date[:4]}/month={execution_date[5:7]}/day={execution_date[8:10]}/
    """
    
    print(message)
    # In production, send via SNS/email
    return message


# Define DAG
with DAG(
    'medical_etl_pipeline',
    default_args=default_args,
    description='ETL pipeline for FDA and clinical trial data',
    schedule='@daily',
    catchup=False,
    tags=['medical', 'etl', 'fda'],
) as dag:
    
    # Start task
    start = EmptyOperator(task_id='start')
    
    # Extraction tasks
    with TaskGroup('extraction', tooltip="Extract data from sources") as extraction:
        
        extract_fda = PythonOperator(
            task_id='extract_fda_data',
            python_callable=extract_fda_data,
        )
        
        extract_ct = PythonOperator(
            task_id='extract_clinical_trials',
            python_callable=extract_clinical_trials,
        )
        
        validate = PythonOperator(
            task_id='validate_extraction',
            python_callable=validate_extraction,
            trigger_rule='all_success',
        )
        
        [extract_fda, extract_ct] >> validate
    
    # Transformation task using Kubernetes
    transform = KubernetesPodOperator(
        task_id='transform_data',
        name='medical-etl-transform',
        namespace='airflow',
        image=DOCKER_IMAGE,
        cmds=['python', '-m', 'src.transformers.drug_transformer'],
        arguments=['--date', '{{ ds }}', '--bucket', S3_BUCKET],
        env_vars={
            'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
            'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'AWS_DEFAULT_REGION': os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
        },
        get_logs=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        config_file=None,
        startup_timeout_seconds=300,
    )
    
    # Data quality checks
    quality_checks = PythonOperator(
        task_id='quality_checks',
        python_callable=quality_check,
    )
    
    # Completion notification
    notify = PythonOperator(
        task_id='send_notification',
        python_callable=send_completion_notification,
    )
    
    # End task
    end = EmptyOperator(task_id='end')
    
    # Define workflow
    start >> extraction >> transform >> quality_checks >> notify >> end
