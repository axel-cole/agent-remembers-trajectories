import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from app.config import config
from app.workflows import AgentRouterWorkflow
from app.activities import retrieve_trajectory, launch_agent


async def main():
    """Start the Temporal worker."""
    # Connect to Temporal
    client = await Client.connect(
        config.TEMPORAL_HOST,
        namespace=config.TEMPORAL_NAMESPACE,
    )

    # Create worker
    worker = Worker(
        client,
        task_queue=config.TEMPORAL_TASK_QUEUE,
        workflows=[AgentRouterWorkflow],
        activities=[retrieve_trajectory, launch_agent],
    )

    print(f"Starting worker on task queue: {config.TEMPORAL_TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
