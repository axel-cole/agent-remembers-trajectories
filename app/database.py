from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError
from typing import Optional
from app.config import config
import json


class TrajectoryDatabase:
    """
    Handles trajectory retrieval from the existing Agent Platform PostgreSQL database.

    This connects to the SAME database that Agent Platform uses - no separate database needed.
    Just configure DB_* variables in .env to point to your Agent Platform database.
    """

    def __init__(self):
        # Connect to the existing Agent Platform database
        self.engine = create_engine(config.POSTGRES_URI)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_similar_trajectory(
        self, task_objective: str, start_url: str, org_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Retrieve the most similar successful trajectory from Agent Platform's database.

        Uses PostgreSQL trigram similarity to match objectives and filters for successful
        trajectories based on feedback_success and absence of errors.

        Args:
            task_objective: The task objective string
            start_url: The starting URL
            org_id: Optional organization ID to filter trajectories

        Returns:
            Formatted trajectory string if found, None otherwise
        """
        try:
            with self.SessionLocal() as session:
                # Enable pg_trgm extension for similarity matching
                try:
                    session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                    session.commit()
                except Exception:
                    # Extension might already exist or user lacks permissions - that's OK
                    pass

                # Find the most similar successful trajectory
                # Priority: answer validation success=True > high similarity score
                # Only retrieve headless trajectories with successful answer validation
                # SECURITY: org_id is REQUIRED to prevent cross-organization data leakage

                if not org_id:
                    print("Warning: No org_id provided - cannot retrieve trajectory without organization context")
                    return None

                # Validate that org_id looks like a UUID to avoid SQL errors
                # Basic check - just ensure it's not a placeholder string
                if org_id in ['your-org-id-here', 'test', 'example']:
                    print(f"Warning: Invalid org_id '{org_id}' - must be a valid UUID from your .env file")
                    return None

                query = text("""
                    SELECT t.id, t.start_url, t.objective,
                           similarity(t.objective, :objective) as sim_score
                    FROM trajectory t
                    WHERE t.start_url = :start_url
                      AND t.status = 'completed'
                      AND t.error IS NULL
                      AND t.run_settings->'web'->>'headless' = 'true'
                      AND similarity(t.objective, :objective) > 0.1
                      AND t.org_id = :org_id
                      AND EXISTS (
                        SELECT 1 FROM trajectory_event te
                        WHERE te.trajectory_id = t.id
                          AND te.type = 'AgentEvent'
                          AND te.data->'event'->>'kind' = 'tool_result'
                          AND te.data->'event'->'tool_req'->>'tool_name' = 'answer'
                          AND (te.data->'event'->>'result') LIKE '%success=True%'
                      )
                    ORDER BY
                      similarity(t.objective, :objective) DESC,
                      t.created_at DESC
                    LIMIT 1
                """)

                params = {"start_url": start_url, "objective": task_objective, "org_id": org_id}
                result = session.execute(query, params).fetchone()

                if not result:
                    return None

                trajectory_id = result[0]

                # Get AgentEvents with tool_result kind (these contain the actions and coordinates)
                events_query = text("""
                    SELECT
                        te.index,
                        te.data->'event'->'tool_req' as tool_req,
                        te.data->'event'->'result' as tool_result
                    FROM trajectory_event te
                    WHERE te.trajectory_id = :trajectory_id
                      AND te.type = 'AgentEvent'
                      AND te.data->'event'->>'kind' = 'tool_result'
                    ORDER BY te.index
                """)

                events = session.execute(
                    events_query, {"trajectory_id": trajectory_id}
                ).fetchall()

                if not events:
                    return None

                # Format events as trajectory steps with full action details
                trajectory_steps = []
                step_num = 1
                for _, tool_req_data, tool_result_data in events:
                    # Skip if tool_req is None
                    if not tool_req_data:
                        continue

                    # Data is already dict from jsonb, but handle string case
                    if isinstance(tool_req_data, str):
                        try:
                            tool_req_data = json.loads(tool_req_data)
                        except json.JSONDecodeError:
                            continue
                    if isinstance(tool_result_data, str):
                        try:
                            tool_result_data = json.loads(tool_result_data)
                        except json.JSONDecodeError:
                            tool_result_data = None

                    # Extract tool action details
                    tool_name = (
                        tool_req_data.get("tool_name", "unknown")
                        if tool_req_data
                        else "unknown"
                    )
                    tool_args = tool_req_data.get("args", {}) if tool_req_data else {}

                    # Skip answer actions - they're the final result, not trajectory steps
                    if tool_name == "answer" or "answer" in tool_name:
                        continue

                    # Simplify tool name (remove _localizer_web, _web suffixes)
                    simplified_name = tool_name.replace("_localizer_web", "").replace(
                        "_web", ""
                    )

                    # Build complete action with all available information
                    action_details = dict(tool_args)  # Start with original args

                    # Add coordinates from localizer_output if available
                    if tool_result_data and "localizer_output" in tool_result_data:
                        localizer_output = tool_result_data["localizer_output"]
                        if "x" in localizer_output and "y" in localizer_output:
                            action_details["coordinates"] = {
                                "x": localizer_output["x"],
                                "y": localizer_output["y"],
                            }

                    # Add viewport size if available
                    if tool_result_data and "viewport_size" in tool_result_data:
                        action_details["viewport_size"] = tool_result_data[
                            "viewport_size"
                        ]

                    # Add any other useful result data
                    if tool_result_data and "element" in tool_result_data:
                        # Only add if not already in args
                        if "element" not in action_details:
                            action_details["element"] = tool_result_data["element"]

                    trajectory_steps.append(
                        f"{step_num}. {simplified_name}({json.dumps(action_details, ensure_ascii=False)})"
                    )
                    step_num += 1

                return "\n".join(trajectory_steps)

        except ProgrammingError as e:
            # Table doesn't exist - that's OK, just return None
            if "does not exist" in str(e):
                return None
            raise
        except Exception as e:
            # Log and return None for any other errors
            print(f"Error retrieving trajectory: {e}")
            return None

    def format_trajectory_as_instructions(self, trajectory: str) -> str:
        """
        Format the trajectory data into instruction text for the prompt.

        This creates the exact format you specified in your example.
        """
        if not trajectory:
            return ""

        # If trajectory is already formatted, return as is
        if isinstance(trajectory, str) and "## Similar Trajectory" in trajectory:
            return trajectory

        # Format according to your specification
        header = "\n# CRITICAL: Execute the reference trajectory EXACTLY\n\n"
        header += "⚠️ DO NOT answer or make assumptions before executing ALL trajectory steps.\n\n"
        header += "You MUST:\n"
        header += "1. Execute EVERY step from the trajectory below with the provided coordinates\n"
        header += "2. Use multiple tool_calls in a SINGLE response to run many steps at once\n"
        header += "3. Wait for observations before answering\n"
        header += "4. ONLY answer after completing the trajectory and seeing the actual data\n\n"
        header += "## Reference Trajectory (execute with exact coordinates):\n\n"

        return header + trajectory
