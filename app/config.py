import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Temporal
    TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
    TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
    TEMPORAL_TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "agent-router-queue")

    # Database - Match Agent Platform's style
    DB_NAME = os.getenv("DB_NAME", "postgres")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")

    @property
    def POSTGRES_URI(self):
        """Build PostgreSQL URI from individual components (Agent Platform style)"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Agent Platform
    AGENT_PLATFORM_URL = os.getenv("AGENT_PLATFORM_URL", "http://localhost:8000")
    AGENT_NAME = os.getenv("AGENT_NAME", "multi-forest")

    # Authentication - for Agent Platform API calls
    AGENT_API_TOKEN = os.getenv("AGENT_API_TOKEN", "")
    AGENT_USER_SUB = os.getenv("AGENT_USER_SUB", "")
    AGENT_USER_ORG = os.getenv("AGENT_USER_ORG", "")

    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8080"))


config = Config()
