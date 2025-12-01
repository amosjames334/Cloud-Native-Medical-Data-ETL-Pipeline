import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

try:
    from src.extractors.fda_extractor import FDAExtractor
    from src.extractors.clinicaltrials_extractor import ClinicalTrialsExtractor
    logger.info("Successfully imported extractors")
except ImportError as e:
    logger.error(f"Failed to import extractors: {e}")
    sys.exit(1)

def test_fda_extraction():
    logger.info("Testing FDA Extractor...")
    try:
        extractor = FDAExtractor()
        # Test with a small limit and wider date range
        data = extractor.extract_drug_events(
            start_date="2024-01-01",
            end_date="2024-01-07",
            limit=5
        )
        logger.info(f"FDA Extraction successful. Retrieved {len(data)} records.")
        print(data.head())
        return True
    except Exception as e:
        logger.error(f"FDA Extraction failed: {e}")
        return False

def test_clinical_trials_extraction():
    logger.info("Testing Clinical Trials Extractor...")
    try:
        extractor = ClinicalTrialsExtractor()
        # Test with a small limit and max_studies to prevent infinite loop
        data = extractor.extract_studies(
            last_update_date="2024-01-01",
            page_size=5,
            max_studies=10
        )
        logger.info(f"Clinical Trials Extraction successful. Retrieved {len(data)} records.")
        print(data.head())
        return True
    except Exception as e:
        logger.error(f"Clinical Trials Extraction failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting local verification...")
    
    fda_success = test_fda_extraction()
    ct_success = test_clinical_trials_extraction()
    
    if fda_success and ct_success:
        logger.info("All local tests passed!")
        sys.exit(0)
    else:
        logger.error("Some tests failed.")
        sys.exit(1)
