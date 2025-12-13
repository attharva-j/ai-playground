"""
Configuration management for the self-correcting multi-agent system.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from the global .env file
load_dotenv(dotenv_path="../.env")

@dataclass
class AgentConfig:
    """Configuration for individual agents."""
    model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout: int = 30

@dataclass
class SystemConfig:
    """System-wide configuration."""
    max_iterations: int = 3
    judge_confidence_threshold: float = 0.8
    enable_tools: bool = True
    log_level: str = "INFO"
    
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    
    # Agent configurations
    solver_config: AgentConfig = field(default_factory=lambda: AgentConfig(temperature=0.1))
    critic_config: AgentConfig = field(default_factory=lambda: AgentConfig(temperature=0.3))
    judge_config: AgentConfig = field(default_factory=lambda: AgentConfig(temperature=0.0))

def get_config() -> SystemConfig:
    """Get the system configuration."""
    return SystemConfig()

def validate_config(config: SystemConfig) -> bool:
    """Validate that required configuration is present."""
    if not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")
    
    if config.max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")
    
    if not (0.0 <= config.judge_confidence_threshold <= 1.0):
        raise ValueError("judge_confidence_threshold must be between 0.0 and 1.0")
    
    return True