"""Configuration settings for the application."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repository root (parent directory)
root_dir = Path(__file__).parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Database Configuration
# Use absolute path for SQLite database in the solution directory
solution_dir = Path(__file__).parent
db_path = solution_dir / "watches_enterprise.db"
# Convert Windows path to forward slashes for SQLite URL
db_path_str = str(db_path).replace("\\", "/")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///watches_enterprise.db")

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "anthropic"
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")  # or "claude-3-sonnet-20240229"

# Application Configuration
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
