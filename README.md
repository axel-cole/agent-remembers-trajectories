# Agent Remembers Trajectories

Temporal-based workflow system that enhances agent tasks by retrieving and replaying successful past trajectories.

## What It Does

Users send requests to your API (same format as Agent Platform). Before executing the agent:
1. Queries **Agent Platform's existing PostgreSQL database** for similar trajectories
2. Enhances the prompt with trajectory instructions
3. Calls Agent Platform with the enhanced prompt using `multi-forest` agent
4. Returns the result

**Key point**: Uses Agent Platform's existing database - no separate database needed!

## Architecture

```
User Request → Agent Router API → Temporal Workflow
                                    ↓
                        Activity 1: Retrieve Trajectory
                        (from Agent Platform's postgres)
                                    ↓
                        Activity 2: Launch Agent
                        (call Agent Platform with enhanced prompt)
                                    ↓
                                 Result
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- Temporal Server (local or cloud)
- Access to Agent Platform's PostgreSQL database
- **Agent Platform with `multi-forest` agent configured** (see requirements below)

## Quick Setup

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure Agent Platform

**IMPORTANT**: The `multi-forest` agent must be configured in Agent Platform with these specific requirements:

1. **Agent name**: `multi-forest` (must exist in Agent Platform)
2. **Multiple tool calls**: Policy must allow outputting multiple tool calls at once
3. **No localizer**: Must NOT use any localizer (coordinates provided by trajectory)
4. **No batching guidelines**: The agent prompt must NOT contain batching guidelines about when to batch actions

The agent should execute trajectory steps with provided coordinates without trying to re-localize elements or apply batching logic.

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your settings:
```bash
# Database credentials (Agent Platform's existing database)
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Agent Platform Configuration
AGENT_PLATFORM_URL=http://localhost:8000
AGENT_NAME=multi-forest

# Authentication for Agent Platform API
AGENT_API_TOKEN=your-api-token-here
AGENT_USER_SUB=your-user-sub-here
AGENT_USER_ORG=your-org-uuid-here

# Temporal Configuration
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=agent-router-queue

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080
```

### 5. Start Temporal server

```bash
temporal server start-dev
```

### 6. Start the worker

In one terminal:
```bash
uv run python -m app.worker
```

### 7. Start the API

In another terminal:
```bash
uv run python -m app.api
```

## API Usage

Send POST request to `/run-agent` with the **exact same format as Agent Platform**:

```bash
curl -X POST http://localhost:8080/run-agent \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "X-User-Org: YOUR_ORG_ID" \
  -d '{
    "task": {
      "objective": "Return the actual departure date for booking PILEH2512010",
      "start_url": "https://nvogo.nvoworldwide.com/tracker"
    },
    "is_public": true
  }'
```

Or use the test script:
```bash
uv run python scripts/example_request.py
```

## How It Works

### Request Flow

1. User sends request to Agent Router API
2. API starts Temporal workflow
3. **Activity 1**: Retrieve trajectory from Agent Platform's postgres
4. **Activity 2**: Call Agent Platform with enhanced prompt
5. Return result to user

### Prompt Enhancement

**Original:**
```
Return the actual departure date for booking PILEH2512010
```

**Enhanced (sent to Agent Platform):**
```
Return the actual departure date for booking PILEH2512010

# CRITICAL: Many actions executed at once

You MUST output as many actions as possible in a SINGLE response with multiple tool_calls.

Reference trajectory provided below. Adapt based on current state.

## Similar Trajectory to adapt if necessary:

1. write({...})
2. click_web({...})
3. wait_web({...})
4. scroll_at_web({...})
```

## Customization

### Trajectory Similarity Search

Edit [app/database.py](app/database.py:20) to customize how trajectories are retrieved:

```python
def get_similar_trajectory(self, task_objective: str, start_url: str) -> Optional[str]:
    # Currently: simple URL matching
    # You can implement:
    # - Vector embeddings (pgvector)
    # - Semantic search
    # - Multiple criteria (URL + objective similarity)
    pass
```

### Prompt Format

Edit [app/database.py](app/database.py:54) to customize how trajectories are formatted:

```python
def format_trajectory_as_instructions(self, trajectory: str) -> str:
    # Customize the instruction format here
    pass
```

## Project Structure

```
agent_router/
├── app/
│   ├── activities.py    # retrieve_trajectory + launch_agent
│   ├── workflows.py     # Temporal workflow orchestration
│   ├── database.py      # Connects to Agent Platform's postgres
│   ├── api.py          # FastAPI endpoint
│   ├── config.py       # Environment configuration
│   ├── models.py       # Pydantic models
│   └── worker.py       # Temporal worker
│
├── scripts/
│   └── example_request.py  # Test script
│
├── .env.example        # Configuration template
├── pyproject.toml      # Dependencies (PEP 621 format)
└── README.md          # This file
```

## Monitoring

- **Temporal UI**: http://localhost:8233
  - View workflow executions
  - Inspect activity logs
  - Retry failed workflows
  - Debug errors

- **API Health**: http://localhost:8080/health

## Troubleshooting

### Worker can't connect to Temporal
```bash
# Ensure Temporal is running
temporal server start-dev
# Check TEMPORAL_HOST in .env
```

### Database connection errors
```bash
# Verify POSTGRES_URI points to Agent Platform's database
# Check that the trajectories table exists
```

### Agent Platform errors
```bash
# Verify AGENT_PLATFORM_URL is correct
# Ensure Agent Platform is running
# Check that multi-forest agent is registered
```

### No trajectories found
- Verify trajectories exist in Agent Platform's database
- Check similarity search logic in [app/database.py](app/database.py)
- May need to adjust query based on your table schema

## About uv

This project uses [uv](https://docs.astral.sh/uv/) for package management:

- **Fast**: 10-100x faster than pip/poetry
- **Simple**: Single tool for everything
- **Standard**: Uses pyproject.toml (PEP 621)
- **Reliable**: Consistent dependency resolution

### Common uv commands

```bash
uv sync              # Install dependencies
uv add <package>     # Add dependency
uv remove <package>  # Remove dependency
uv run python -m app # Run Python module
uv sync --upgrade    # Upgrade dependencies
```

## Production Deployment

For production:

1. Use managed Temporal (Temporal Cloud or self-hosted cluster)
2. Point to Agent Platform's production database
3. Deploy worker and API as separate services
4. Use proper secrets management (not `.env` files)
5. Add monitoring and alerting
6. Configure proper retry policies and timeouts
7. Set up CI/CD pipeline

## License

MIT
