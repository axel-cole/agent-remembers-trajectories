from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any, Optional

with workflow.unsafe.imports_passed_through():
    from app.activities import retrieve_trajectory, launch_agent


@workflow.defn
class AgentRouterWorkflow:
    """
    Workflow that orchestrates the agent execution pipeline:
    1. Retrieve similar trajectory from database
    2. Enhance prompt with trajectory instructions
    3. Launch agent via Agent Platform
    """

    @workflow.run
    async def run(self, task: Dict[str, Any], is_public: bool, org_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the agent workflow.

        Args:
            task: Dict with 'objective' and 'start_url'
            is_public: Whether the task is public
            org_id: Optional organization ID to filter trajectories

        Returns:
            Result from agent execution
        """
        workflow.logger.info(f"Starting workflow for task: {task}, org_id: {org_id}")

        # Step 1: Retrieve and enhance with trajectory (filtered by org if provided)
        enhanced_task = await workflow.execute_activity(
            retrieve_trajectory,
            args=[task, org_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
            ),
        )

        workflow.logger.info(f"Enhanced task with trajectory")

        # Step 2: Launch agent with enhanced task
        result = await workflow.execute_activity(
            launch_agent,
            args=[enhanced_task, is_public],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(seconds=30),
            ),
        )

        workflow.logger.info(f"Workflow completed")
        return result
