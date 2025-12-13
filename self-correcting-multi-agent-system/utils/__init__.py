"""
Utility modules for the self-correcting multi-agent system.
"""

from .config import SystemConfig, AgentConfig, get_config, validate_config
from .logger import SystemLogger, AgentInteraction, SystemExecution, logger
from .prompts import (
    SOLVER_SYSTEM_PROMPT,
    CRITIC_SYSTEM_PROMPT, 
    JUDGE_SYSTEM_PROMPT,
    get_solver_prompt,
    get_critic_prompt,
    get_judge_prompt
)

__all__ = [
    'SystemConfig', 'AgentConfig', 'get_config', 'validate_config',
    'SystemLogger', 'AgentInteraction', 'SystemExecution', 'logger',
    'SOLVER_SYSTEM_PROMPT', 'CRITIC_SYSTEM_PROMPT', 'JUDGE_SYSTEM_PROMPT',
    'get_solver_prompt', 'get_critic_prompt', 'get_judge_prompt'
]