"""
Structured logging for the self-correcting multi-agent system.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class AgentInteraction:
    """Record of a single agent interaction."""
    agent_type: str
    input_prompt: str
    output: str
    timestamp: float
    tokens_used: int = 0
    latency_ms: float = 0.0
    confidence: float = 0.0
    metadata: Dict[str, Any] = None

@dataclass
class SystemExecution:
    """Record of a complete system execution."""
    session_id: str
    question: str
    context: str
    final_answer: str
    decision: str  # PASS/FAIL
    confidence: float
    iterations: int
    total_tokens: int
    total_latency_ms: float
    interactions: List[AgentInteraction]
    timestamp: float
    metadata: Dict[str, Any] = None

class SystemLogger:
    """Logger for tracking multi-agent system performance."""
    
    def __init__(self, log_dir: str = "data/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[SystemExecution] = None
        self.interactions: List[AgentInteraction] = []
    
    def start_session(self, session_id: str, question: str, context: str = "") -> None:
        """Start a new logging session."""
        self.current_session = SystemExecution(
            session_id=session_id,
            question=question,
            context=context,
            final_answer="",
            decision="",
            confidence=0.0,
            iterations=0,
            total_tokens=0,
            total_latency_ms=0.0,
            interactions=[],
            timestamp=time.time(),
            metadata={}
        )
        self.interactions = []
    
    def log_agent_interaction(
        self,
        agent_type: str,
        input_prompt: str,
        output: str,
        tokens_used: int = 0,
        latency_ms: float = 0.0,
        confidence: float = 0.0,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Log a single agent interaction."""
        interaction = AgentInteraction(
            agent_type=agent_type,
            input_prompt=input_prompt,
            output=output,
            timestamp=time.time(),
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            confidence=confidence,
            metadata=metadata or {}
        )
        self.interactions.append(interaction)
    
    def end_session(
        self,
        final_answer: str,
        decision: str,
        confidence: float,
        iterations: int,
        metadata: Dict[str, Any] = None
    ) -> None:
        """End the current session and save logs."""
        if not self.current_session:
            raise ValueError("No active session to end")
        
        self.current_session.final_answer = final_answer
        self.current_session.decision = decision
        self.current_session.confidence = confidence
        self.current_session.iterations = iterations
        self.current_session.interactions = self.interactions.copy()
        self.current_session.total_tokens = sum(i.tokens_used for i in self.interactions)
        self.current_session.total_latency_ms = sum(i.latency_ms for i in self.interactions)
        self.current_session.metadata = metadata or {}
        
        # Save to file
        self._save_session()
        
        # Reset for next session
        self.current_session = None
        self.interactions = []
    
    def _save_session(self) -> None:
        """Save the current session to a JSON file."""
        if not self.current_session:
            return
        
        timestamp = datetime.fromtimestamp(self.current_session.timestamp)
        filename = f"session_{self.current_session.session_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.log_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(self.current_session), f, indent=2)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        if not self.current_session:
            return {}
        
        return {
            "session_id": self.current_session.session_id,
            "question": self.current_session.question,
            "iterations": len(self.interactions),
            "total_tokens": sum(i.tokens_used for i in self.interactions),
            "total_latency_ms": sum(i.latency_ms for i in self.interactions),
            "agent_calls": {
                agent_type: len([i for i in self.interactions if i.agent_type == agent_type])
                for agent_type in set(i.agent_type for i in self.interactions)
            }
        }
    
    def load_sessions(self, limit: int = None) -> List[SystemExecution]:
        """Load previous sessions from log files."""
        sessions = []
        log_files = sorted(self.log_dir.glob("session_*.json"))
        
        if limit:
            log_files = log_files[-limit:]
        
        for filepath in log_files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    # Convert back to dataclass
                    interactions = [AgentInteraction(**i) for i in data['interactions']]
                    data['interactions'] = interactions
                    sessions.append(SystemExecution(**data))
            except Exception as e:
                print(f"Error loading session from {filepath}: {e}")
        
        return sessions

# Global logger instance
logger = SystemLogger()