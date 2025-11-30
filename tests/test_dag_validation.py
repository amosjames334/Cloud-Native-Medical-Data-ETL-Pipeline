"""
DAG Validation Tests for CI/CD Pipeline
Tests DAG syntax, imports, and structure
"""

import os
import sys
import pytest
from airflow.models import DagBag

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DAG_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'dags')


class TestDAGValidation:
    """Test suite for DAG validation"""
    
    def test_dag_bag_import(self):
        """Test that all DAGs can be imported without errors"""
        dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
        
        assert len(dag_bag.import_errors) == 0, \
            f"DAG import errors: {dag_bag.import_errors}"
        
        assert len(dag_bag.dags) > 0, "No DAGs found"
    
    def test_no_dag_cycles(self):
        """Test that DAGs don't have circular dependencies"""
        dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
        
        for dag_id, dag in dag_bag.dags.items():
            if len(dag.tasks) == 0:
                continue
            try:
                # topological_sort will raise an exception if there's a cycle
                dag.topological_sort()
            except Exception as e:
                pytest.fail(f"DAG {dag_id} has a cycle: {e}")
    
    def test_dag_has_tags(self):
        """Test that all DAGs have tags"""
        dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
        
        for dag_id, dag in dag_bag.dags.items():
            assert len(dag.tags) > 0, f"DAG {dag_id} has no tags"
    
    def test_dag_has_owner(self):
        """Test that all DAGs have an owner"""
        dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
        
        for dag_id, dag in dag_bag.dags.items():
            assert dag.owner is not None, f"DAG {dag_id} has no owner"
            assert dag.owner != 'airflow', \
                f"DAG {dag_id} should have a specific owner, not 'airflow'"
    
    def test_dag_has_retries(self):
        """Test that all DAGs have retry configuration"""
        dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
        
        for dag_id, dag in dag_bag.dags.items():
            assert dag.default_args.get('retries') is not None, \
                f"DAG {dag_id} has no retry configuration"
    
    def test_medical_etl_dag_structure(self):
        """Test specific structure of medical_etl_pipeline DAG"""
        dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
        
        assert 'medical_etl_pipeline' in dag_bag.dags, \
            "medical_etl_pipeline DAG not found"
        
        dag = dag_bag.dags['medical_etl_pipeline']
        
        # Check required tasks exist
        required_tasks = [
            'start',
            'extraction.extract_fda_data',
            'extraction.extract_clinical_trials',
            'extraction.validate_extraction',
            'transform_data',
            'quality_checks',
            'send_notification',
            'end'
        ]
        
        task_ids = [task.task_id for task in dag.tasks]
        
        for required_task in required_tasks:
            assert required_task in task_ids, \
                f"Required task '{required_task}' not found in DAG"
    
    def test_dag_schedule_interval(self):
        """Test that DAGs have appropriate schedule intervals"""
        dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
        
        for dag_id, dag in dag_bag.dags.items():
            assert dag.schedule_interval is not None, \
                f"DAG {dag_id} has no schedule interval"
    
    def test_dag_catchup_disabled(self):
        """Test that catchup is disabled for production DAGs"""
        dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
        
        for dag_id, dag in dag_bag.dags.items():
            assert dag.catchup is False, \
                f"DAG {dag_id} should have catchup=False for production"
    
    def test_task_timeout_configured(self):
        """Test that tasks have execution timeout configured"""
        dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
        
        for dag_id, dag in dag_bag.dags.items():
            execution_timeout = dag.default_args.get('execution_timeout')
            assert execution_timeout is not None, \
                f"DAG {dag_id} has no execution_timeout configured"


class TestDAGConfiguration:
    """Test DAG configuration files"""
    
    def test_pipeline_config_exists(self):
        """Test that pipeline configuration file exists"""
        config_path = os.path.join(DAG_FOLDER, 'config', 'pipeline_config.yaml')
        assert os.path.exists(config_path), \
            "pipeline_config.yaml not found"
    
    def test_pipeline_config_valid(self):
        """Test that pipeline configuration is valid YAML"""
        import yaml
        
        config_path = os.path.join(DAG_FOLDER, 'config', 'pipeline_config.yaml')
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config is not None, "Configuration is empty"
        assert 'extraction' in config, "Missing 'extraction' section"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
