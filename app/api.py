from fastapi import FastAPI, HTTPException, Request
from temporalio.client import Client
import uuid
from app.config import config
from app.models import AgentRequest
from app.workflows import AgentRouterWorkflow

app = FastAPI(title="Agent Router API")


async def get_temporal_client() -> Client:
    """Get Temporal client instance."""
    return await Client.connect(
        config.TEMPORAL_HOST,
        namespace=config.TEMPORAL_NAMESPACE,
    )


@app.post("/run-agent")
async def run_agent(agent_request: AgentRequest, request: Request):
    """
    Execute an agent task with trajectory-based prompt enhancement.

    This endpoint maintains the same interface as Agent Platform,
    but adds trajectory retrieval and prompt enhancement.

    Returns the Agent Platform trajectory response directly.
    """
    try:
        # Extract org_id from headers (matching Agent Platform's X-User-Org header)
        org_id = request.headers.get("X-User-Org")

        # Connect to Temporal
        client = await get_temporal_client()

        # Generate unique workflow ID
        workflow_id = f"agent-router-{uuid.uuid4()}"

        # Start workflow with org_id for trajectory filtering
        handle = await client.start_workflow(
            AgentRouterWorkflow.run,
            args=[agent_request.task.dict(), agent_request.is_public, org_id],
            id=workflow_id,
            task_queue=config.TEMPORAL_TASK_QUEUE,
        )

        # Wait for workflow to complete
        result = await handle.result()

        # Return Agent Platform response directly (no wrapper)
        if result.get("success"):
            return result.get("result")
        else:
            # If there was an error, raise HTTPException
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error occurred")
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )
