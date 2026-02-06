"""
Example script to test the Agent Router API.

Make sure to set these environment variables in your .env file:
- AGENT_API_TOKEN: Your API token
- AGENT_USER_ORG: Your organization ID (must be a valid UUID)
"""

import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


async def test_agent_router():
    """Send a test request to the Agent Router API."""
    payload = {
        "task": {
            "objective": "Return the actual departure date in the following timestamp format YYYY-MM-DDTHH:MM:SS±HH:MM for the booking number SFSI25075458. The answer format should be the date only.",
            "start_url": "https://nvogo.nvoworldwide.com/tracker",
        },
        "is_public": True,
    }

    # Headers matching Agent Platform's authentication pattern
    # These will be read from environment variables (set in .env file)
    api_token = os.getenv("AGENT_API_TOKEN")
    org_id = os.getenv("AGENT_USER_ORG")

    if not api_token:
        print("Error: AGENT_API_TOKEN must be set in environment or .env file")
        return

    if not org_id:
        print(
            "Error: AGENT_USER_ORG must be set in environment or .env file (must be a valid UUID)"
        )
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}",
        "X-User-Org": org_id,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/run-agent",
            json=payload,
            headers=headers,
            timeout=300.0,
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


if __name__ == "__main__":
    asyncio.run(test_agent_router())
