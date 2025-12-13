"""
Orchestrator - Controls the flow and coordination of the multi-agent system.
"""

import uuid
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from .solver_agent import SolverAgent, SolverResponse
from .critic_agent import CriticAgent, CriticResponse, CriticDecision
from .judge_agent import JudgeAgent, JudgeResponse, JudgeDecision
from utils.config import SystemConfig, get_config, validate_config
from utils.logger import logger

@dataclass
class IterationResult:
    """Result of a single iteration in the multi-agent process."""
    iteration: int
    solver_response: SolverResponse
    critic_response: Optional[CriticResponse]
    judge_response: Optional[JudgeResponse]
    accepted: bool
    reason: str

@dataclass
class SystemResult:
    """Final result from the multi-agent system."""
    session_id: str
    question: str
    context: str
    final_answer: str
    accepted: bool
    confidence: float
    iterations: List[IterationResult]
    total_iterations: int
    total_tokens: int
    total_latency_ms: float
    metadata: Dict[str, Any]

class Orchestrator:
    """
    Orchestrator manages the interaction between Solver, Critic, and Judge agents.
    
    This class implements the core logic for the self-correcting multi-agent system,
    managing iteration cycles, decision making, and result aggregation.
    """
    
    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or get_config()
        validate_config(self.config)
        
        # Initialize agents
        self.solver = SolverAgent(self.config.solver_config)
        self.critic = CriticAgent(self.config.critic_config)
        self.judge = JudgeAgent(self.config.judge_config)
        
        self.name = "Orchestrator"
    
    def process(self, question: str, context: str = "") -> SystemResult:
        """
        Process a question through the multi-agent system.
        
        Args:
            question: The question to solve
            context: Additional context or background information
            
        Returns:
            SystemResult with complete processing results
        """
        session_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Start logging session
        logger.start_session(session_id, question, context)
        
        iterations = []
        current_response = None
        accepted = False
        final_confidence = 0.0
        
        try:
            for iteration in range(1, self.config.max_iterations + 1):
                print(f"\n--- Iteration {iteration} ---")
                
                # Step 1: Solver generates or revises solution
                if iteration == 1:
                    solver_response = self.solver.solve(question, context)
                else:
                    # Use critic feedback to improve solution
                    revision_context = self._build_revision_context(
                        question, context, iterations[-1].critic_response
                    )
                    solver_response = self.solver.solve(question, revision_context)
                
                print(f"Solver confidence: {solver_response.confidence:.2f}")
                
                # Step 2: Critic reviews the solution
                critic_response = self.critic.critique(question, solver_response.answer, context)
                print(f"Critic decision: {critic_response.status.value} (confidence: {critic_response.confidence:.2f})")
                
                # Step 3: If critic approves, get judge validation
                judge_response = None
                iteration_accepted = False
                reason = ""
                
                if critic_response.status == CriticDecision.APPROVE:
                    judge_response = self.judge.validate(question, solver_response.answer, context)
                    print(f"Judge decision: {judge_response.decision.value} (confidence: {judge_response.confidence:.2f})")
                    
                    if self.judge.should_accept(judge_response, self.config.judge_confidence_threshold):
                        iteration_accepted = True
                        accepted = True
                        final_confidence = judge_response.confidence
                        reason = "Approved by critic and passed judge validation"
                        current_response = solver_response
                    else:
                        reason = f"Judge rejected: {self.judge.get_rejection_reason(judge_response)}"
                else:
                    reason = f"Critic rejected with {len(critic_response.issues)} issues"
                
                # Record iteration
                iteration_result = IterationResult(
                    iteration=iteration,
                    solver_response=solver_response,
                    critic_response=critic_response,
                    judge_response=judge_response,
                    accepted=iteration_accepted,
                    reason=reason
                )
                iterations.append(iteration_result)
                
                print(f"Iteration result: {reason}")
                
                # Break if accepted or if this is the last iteration
                if iteration_accepted or iteration == self.config.max_iterations:
                    if not iteration_accepted and iteration == self.config.max_iterations:
                        # Use best available response
                        current_response = solver_response
                        final_confidence = min(solver_response.confidence, critic_response.confidence)
                        reason = f"Max iterations reached. Using best available response."
                    break
            
            # Prepare final result
            final_answer = current_response.answer if current_response else "No solution generated"
            total_latency_ms = (time.time() - start_time) * 1000
            
            result = SystemResult(
                session_id=session_id,
                question=question,
                context=context,
                final_answer=final_answer,
                accepted=accepted,
                confidence=final_confidence,
                iterations=iterations,
                total_iterations=len(iterations),
                total_tokens=0,  # Will be calculated from logs
                total_latency_ms=total_latency_ms,
                metadata={
                    "max_iterations_reached": len(iterations) >= self.config.max_iterations,
                    "judge_threshold": self.config.judge_confidence_threshold,
                    "final_reason": reason
                }
            )
            
            # End logging session
            logger.end_session(
                final_answer=final_answer,
                decision="PASS" if accepted else "FAIL",
                confidence=final_confidence,
                iterations=len(iterations),
                metadata=result.metadata
            )
            
            return result
            
        except Exception as e:
            # Handle any system-level errors
            error_result = SystemResult(
                session_id=session_id,
                question=question,
                context=context,
                final_answer=f"System error: {str(e)}",
                accepted=False,
                confidence=0.0,
                iterations=iterations,
                total_iterations=len(iterations),
                total_tokens=0,
                total_latency_ms=(time.time() - start_time) * 1000,
                metadata={"error": str(e)}
            )
            
            logger.end_session(
                final_answer=error_result.final_answer,
                decision="FAIL",
                confidence=0.0,
                iterations=len(iterations),
                metadata=error_result.metadata
            )
            
            return error_result
    
    def _build_revision_context(
        self, 
        question: str, 
        original_context: str, 
        critic_response: CriticResponse
    ) -> str:
        """
        Build context for solver revision based on critic feedback.
        
        Args:
            question: Original question
            original_context: Original context
            critic_response: Critic's feedback
            
        Returns:
            Enhanced context for revision
        """
        revision_context = original_context
        
        if original_context:
            revision_context += "\n\n"
        
        revision_context += "REVISION GUIDANCE:\n"
        revision_context += "The previous solution was critiqued. Please address the following:\n\n"
        
        if critic_response.issues:
            revision_context += "Issues to fix:\n"
            for i, issue in enumerate(critic_response.issues, 1):
                revision_context += f"{i}. {issue}\n"
            revision_context += "\n"
        
        if critic_response.suggestions:
            revision_context += "Suggestions to implement:\n"
            for i, suggestion in enumerate(critic_response.suggestions, 1):
                revision_context += f"{i}. {suggestion}\n"
            revision_context += "\n"
        
        if critic_response.missing:
            revision_context += "Missing information to add:\n"
            for i, missing in enumerate(critic_response.missing, 1):
                revision_context += f"{i}. {missing}\n"
            revision_context += "\n"
        
        revision_context += "Please provide an improved solution that addresses these points."
        
        return revision_context
    
    def get_performance_summary(self, result: SystemResult) -> Dict[str, Any]:
        """
        Generate a performance summary for a system result.
        
        Args:
            result: The system result to summarize
            
        Returns:
            Dictionary with performance metrics
        """
        summary = {
            "session_id": result.session_id,
            "success": result.accepted,
            "final_confidence": result.confidence,
            "iterations_used": result.total_iterations,
            "max_iterations": self.config.max_iterations,
            "efficiency": 1.0 - (result.total_iterations - 1) / max(self.config.max_iterations - 1, 1),
            "total_latency_ms": result.total_latency_ms,
            "avg_latency_per_iteration": result.total_latency_ms / max(result.total_iterations, 1)
        }
        
        # Add iteration-specific metrics
        if result.iterations:
            solver_confidences = [it.solver_response.confidence for it in result.iterations]
            critic_confidences = [it.critic_response.confidence for it in result.iterations if it.critic_response]
            
            summary.update({
                "avg_solver_confidence": sum(solver_confidences) / len(solver_confidences),
                "final_solver_confidence": solver_confidences[-1],
                "avg_critic_confidence": sum(critic_confidences) / len(critic_confidences) if critic_confidences else 0.0,
                "critic_approvals": sum(1 for it in result.iterations if it.critic_response and it.critic_response.status == CriticDecision.APPROVE),
                "judge_passes": sum(1 for it in result.iterations if it.judge_response and it.judge_response.decision == JudgeDecision.PASS)
            })
        
        return summary
    
    def compare_single_vs_multi_agent(self, question: str, context: str = "") -> Dict[str, Any]:
        """
        Compare single-agent vs multi-agent performance on the same question.
        
        Args:
            question: Question to solve
            context: Additional context
            
        Returns:
            Comparison results
        """
        # Single-agent approach (just solver)
        single_start = time.time()
        single_response = self.solver.solve(question, context)
        single_latency = (time.time() - single_start) * 1000
        
        # Multi-agent approach
        multi_result = self.process(question, context)
        
        comparison = {
            "question": question,
            "single_agent": {
                "answer": single_response.answer,
                "confidence": single_response.confidence,
                "latency_ms": single_latency,
                "tokens": 0,  # Would need to track from logs
                "validated": False
            },
            "multi_agent": {
                "answer": multi_result.final_answer,
                "confidence": multi_result.confidence,
                "latency_ms": multi_result.total_latency_ms,
                "tokens": multi_result.total_tokens,
                "validated": multi_result.accepted,
                "iterations": multi_result.total_iterations
            },
            "improvement": {
                "confidence_gain": multi_result.confidence - single_response.confidence,
                "latency_cost": multi_result.total_latency_ms - single_latency,
                "validation_added": multi_result.accepted,
                "iteration_overhead": multi_result.total_iterations - 1
            }
        }
        
        return comparison