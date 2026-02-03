#!/usr/bin/env python3
"""
Task Autocomplete Cache Refresh Job

This script refreshes the task autocomplete cache for all known company+role combinations.
It should be run daily via cron or a task scheduler.

Usage:
    python -m jobs.task_autocomplete_refresh

Cron setup (daily at 2 AM):
    0 2 * * * cd /path/to/etter-backend && python -m jobs.task_autocomplete_refresh
"""

import sys
import os
import logging
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from settings.database import get_db
from services.task_autocomplete_service import refresh_all_task_autocomplete_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/task_autocomplete_refresh.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """
    Main function to refresh all task autocomplete caches.
    """
    logger.info("=" * 80)
    logger.info("Starting task autocomplete cache refresh job")
    logger.info(f"Job started at: {datetime.utcnow().isoformat()}")
    logger.info("=" * 80)

    db: Session = next(get_db())

    try:
        result = refresh_all_task_autocomplete_cache(db)

        logger.info("=" * 80)
        logger.info("Job completed successfully")
        logger.info(f"Job finished at: {datetime.utcnow().isoformat()}")
        logger.info(f"Total combinations: {result.get('total_combinations', 0)}")
        logger.info(f"Successful: {result.get('successful', 0)}")
        logger.info(f"Failed: {result.get('failed', 0)}")
        logger.info("=" * 80)

        # Log failed items if any
        if result.get('failed', 0) > 0:
            logger.warning("Failed to refresh the following company+role combinations:")
            for item in result.get('results', []):
                if item.get('status') == 'error':
                    logger.warning(f"  - {item.get('company')}+{item.get('role')}: {item.get('error')}")

        # Exit with non-zero status if there were failures
        if result.get('failed', 0) > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error during refresh job: {str(e)}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
