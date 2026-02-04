"""
Worker entry point for Etter Workflows.

This module provides:
1. Temporal worker configuration and startup
2. Activity and workflow registration
3. CLI for running the worker

Usage:
    # Run the worker
    python -m etter_workflows.worker

    # Or via entry point
    etter-worker

    # Run with specific configuration
    ETTER_TEMPORAL_HOST=localhost ETTER_TEMPORAL_PORT=7233 etter-worker
"""

import asyncio
import logging
import signal
import sys
from typing import List, Optional

from etter_workflows.config.settings import get_settings, load_settings_from_env
from etter_workflows.activities.role_setup import (
    create_company_role,
    link_job_description,
)
from etter_workflows.activities.ai_assessment import run_ai_assessment
from etter_workflows.workflows.role_onboarding import RoleOnboardingWorkflow

logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Manager for Temporal worker lifecycle.

    Handles:
    - Worker configuration
    - Activity registration
    - Workflow registration
    - Graceful shutdown
    """

    def __init__(self):
        """Initialize worker manager."""
        self.settings = get_settings()
        self.worker = None
        self.client = None
        self._shutdown_event = asyncio.Event()

    async def connect(self):
        """
        Connect to Temporal server.

        Note: This requires temporalio package to be installed.
        If not available, falls back to standalone mode.
        """
        try:
            from temporalio.client import Client
            from temporalio.worker import Worker

            logger.info(f"Connecting to Temporal at {self.settings.temporal_address}")

            self.client = await Client.connect(
                self.settings.temporal_address,
                namespace=self.settings.get_temporal_namespace(),
            )

            logger.info(
                f"Connected to Temporal namespace: {self.settings.get_temporal_namespace()}"
            )

            return True

        except ImportError:
            logger.warning(
                "temporalio package not installed. "
                "Worker will run in standalone mode without Temporal."
            )
            return False

        except Exception as e:
            logger.error(f"Failed to connect to Temporal: {e}")
            return False

    async def start_worker(self):
        """
        Start the Temporal worker.

        Registers activities and workflows, then starts processing.
        """
        if not self.client:
            logger.warning("No Temporal client. Running in standalone mode.")
            return

        try:
            from temporalio.worker import Worker, UnsandboxedWorkflowRunner

            # Define activities
            activities = [
                create_company_role,
                link_job_description,
                run_ai_assessment,
            ]

            # Define workflows
            workflows = [
                RoleOnboardingWorkflow,
            ]

            logger.info(
                f"Starting worker on task queue: {self.settings.temporal_task_queue}"
            )
            logger.info(f"Registered activities: {[a.__name__ for a in activities]}")
            logger.info(f"Registered workflows: {[w.__name__ for w in workflows]}")

            # Use UnsandboxedWorkflowRunner to disable sandbox restrictions
            # This is necessary because our Pydantic models use datetime.utcnow()
            # in default_factory which the sandbox detects and restricts.
            # Note: This means workflows must be careful about determinism.
            self.worker = Worker(
                self.client,
                task_queue=self.settings.temporal_task_queue,
                activities=activities,
                workflows=workflows,
                max_concurrent_activities=self.settings.temporal_max_concurrent_activities,
                workflow_runner=UnsandboxedWorkflowRunner(),
            )

            # Run until shutdown
            await self.worker.run()

        except Exception as e:
            logger.error(f"Worker failed: {e}")
            raise

    async def shutdown(self):
        """Graceful shutdown of the worker."""
        logger.info("Shutting down worker...")

        if self.worker:
            # Signal worker to stop
            self._shutdown_event.set()

        if self.client:
            # Close client connection
            pass

        logger.info("Worker shutdown complete")


async def run_standalone_workflow(
    company_id: str,
    role_name: str,
    use_mock: bool = True,
):
    """
    Run workflow in standalone mode (without Temporal).

    This is useful for testing and development when Temporal
    is not available.

    Args:
        company_id: Company identifier
        role_name: Role name
        use_mock: Use mock AI assessment
    """
    from etter_workflows.workflows.role_onboarding import execute_role_onboarding

    logger.info(f"Running standalone workflow for {role_name} at {company_id}")

    result = await execute_role_onboarding(
        company_id=company_id,
        role_name=role_name,
        use_mock_assessment=use_mock,
    )

    if result.success:
        logger.info(f"Workflow completed successfully!")
        logger.info(f"  Role ID: {result.role_id}")
        logger.info(f"  Dashboard URL: {result.dashboard_url}")
        if result.outputs:
            logger.info(f"  AI Score: {result.outputs.final_score}")
    else:
        logger.error(f"Workflow failed: {result.error}")

    return result


def setup_logging():
    """Configure logging for the worker."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def handle_signals(manager: WorkerManager, loop: asyncio.AbstractEventLoop):
    """Setup signal handlers for graceful shutdown."""
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(manager.shutdown()),
        )


async def main_async():
    """Main async entry point."""
    setup_logging()
    settings = get_settings()

    logger.info("Etter Workflows Worker Starting")
    logger.info(f"  Environment: {settings.environment}")
    logger.info(f"  Temporal Address: {settings.temporal_address}")
    logger.info(f"  Namespace: {settings.get_temporal_namespace()}")
    logger.info(f"  Task Queue: {settings.temporal_task_queue}")
    logger.info(f"  Mock Data: {'enabled' if settings.enable_mock_data else 'disabled'}")

    manager = WorkerManager()

    # Connect to Temporal
    connected = await manager.connect()

    if connected:
        # Start worker with Temporal
        await manager.start_worker()
    else:
        # Failed to connect to Temporal - exit with error
        logger.error("=" * 60)
        logger.error("FAILED TO CONNECT TO TEMPORAL SERVER")
        logger.error("=" * 60)
        logger.error(f"  Address: {settings.temporal_address}")
        logger.error(f"  Namespace: {settings.get_temporal_namespace()}")
        logger.error("")
        logger.error("Please ensure:")
        logger.error("  1. Temporal server is running")
        logger.error("  2. ETTER_TEMPORAL_HOST and ETTER_TEMPORAL_PORT are set correctly")
        logger.error("  3. Network connectivity to Temporal server")
        logger.error("=" * 60)
        sys.exit(1)


def main():
    """Main entry point for the worker."""
    try:
        # Load environment variables
        load_settings_from_env()

        # Run async main
        asyncio.run(main_async())

    except KeyboardInterrupt:
        logger.info("Worker interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
