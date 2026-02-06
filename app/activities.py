from temporalio import activity
from typing import Dict, Any, Optional
import httpx
from app.config import config
from app.database import TrajectoryDatabase
from app.models import Task


@activity.defn
async def retrieve_trajectory(task: Dict[str, Any], org_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Activity to retrieve similar trajectory from database and enhance the prompt.

    Args:
        task: Original task dict with objective and start_url
        org_id: Optional organization ID to filter trajectories

    Returns:
        Enhanced task dict with trajectory instructions added to objective
    """
    activity.logger.info(f"Retrieving trajectory for task: {task}, org_id: {org_id}")

    db = TrajectoryDatabase()

    # Extract task details
    objective = task["objective"]
    start_url = task["start_url"]

    # Find similar trajectory (optionally filtered by org_id)
    trajectory = db.get_similar_trajectory(objective, start_url, org_id)

    if trajectory:
        activity.logger.info("Found similar trajectory, enhancing prompt")
        # Format trajectory as instructions
        trajectory_instructions = db.format_trajectory_as_instructions(trajectory)

        # Enhance the objective with trajectory
        enhanced_objective = f"{objective}{trajectory_instructions}"

        return {
            "objective": enhanced_objective,
            "start_url": start_url
        }
    else:
        activity.logger.warning("No similar trajectory found, using original task")
        return task


@activity.defn
async def launch_agent(task: Dict[str, Any], is_public: bool) -> Dict[str, Any]:
    """
    Activity to launch the agent via Agent Platform API.

    Args:
        task: Enhanced task dict with objective and start_url
        is_public: Whether the task is public

    Returns:
        Result from Agent Platform
    """
    activity.logger.info(f"Launching agent with task: {task}")

    # Prepare the request payload matching Agent Platform's expected format
    payload = {
        "task": {
            "objective": task["objective"],
            "start_url": task["start_url"]
        },
        "is_public": is_public
    }

    # Call Agent Platform's actual endpoint: /api/v1/agents/{agent_name}/trajectories
    url = f"{config.AGENT_PLATFORM_URL}/api/v1/agents/{config.AGENT_NAME}/trajectories"

    # Prepare authentication headers
    headers = {
        "Content-Type": "application/json"
    }
    if config.AGENT_API_TOKEN:
        headers["Authorization"] = f"Bearer {config.AGENT_API_TOKEN}"
    if config.AGENT_USER_SUB:
        headers["X-User-Sub"] = config.AGENT_USER_SUB
    if config.AGENT_USER_ORG:
        headers["X-User-Org"] = config.AGENT_USER_ORG

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            activity.logger.info(f"Calling Agent Platform: POST {url}")
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            activity.logger.info(f"Agent execution completed successfully")
            return {
                "success": True,
                "result": result
            }
        except httpx.HTTPError as e:
            activity.logger.error(f"Agent execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
