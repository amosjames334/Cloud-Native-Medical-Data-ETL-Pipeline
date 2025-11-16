"""
Logging Utility
Configures logging for the ETL pipeline
"""

import logging
import sys
from datetime import datetime


def get_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """
    Get configured logger instance
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, level.upper()))
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        
        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
    
    return logger


class PipelineLogger:
    """
    Context manager for pipeline execution logging
    """
    
    def __init__(self, pipeline_name: str, execution_date: str):
        """
        Initialize pipeline logger
        
        Args:
            pipeline_name: Name of the pipeline
            execution_date: Execution date
        """
        self.pipeline_name = pipeline_name
        self.execution_date = execution_date
        self.logger = get_logger(pipeline_name)
        self.start_time = None
        
    def __enter__(self):
        """Start pipeline logging"""
        self.start_time = datetime.now()
        self.logger.info(f"=" * 80)
        self.logger.info(f"Starting pipeline: {self.pipeline_name}")
        self.logger.info(f"Execution date: {self.execution_date}")
        self.logger.info(f"Start time: {self.start_time}")
        self.logger.info(f"=" * 80)
        return self.logger
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End pipeline logging"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        self.logger.info(f"=" * 80)
        if exc_type is None:
            self.logger.info(f"Pipeline completed successfully: {self.pipeline_name}")
        else:
            self.logger.error(f"Pipeline failed: {self.pipeline_name}")
            self.logger.error(f"Error: {exc_val}")
        
        self.logger.info(f"End time: {end_time}")
        self.logger.info(f"Duration: {duration}")
        self.logger.info(f"=" * 80)
        
        # Don't suppress exceptions
        return False


if __name__ == '__main__':
    # Test logger
    logger = get_logger(__name__)
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test pipeline logger
    with PipelineLogger("test_pipeline", "2024-01-01") as pipeline_log:
        pipeline_log.info("Processing step 1")
        pipeline_log.info("Processing step 2")
        pipeline_log.info("Processing step 3")