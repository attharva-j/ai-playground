"""
Solver Agent - Primary problem-solving agent in the multi-agent system.
"""

import time
from typing import Dict, Any, Optional, List
from openai import OpenAI
from pydantic import BaseModel

from utils.config import AgentConfig
from utils.prompts import get_solver_prompt
from utils.logger import logger

class SolverResponse(BaseModel):
    """Structured response from the Solver Agent."""
    answer: str
    reasoning: str
    evidence: str
    confidence: float
    assumptions: str
    tool_calls: List[str] = []

class SolverAgent:
    """
    Solver Agent responsible for generating initial solutions to problems.
    
    This agent focuses on accuracy and thoroughness, using available tools
    when necessary and providing detailed reasoning for its solutions.
    """
    
    def __init__(self, config: AgentConfig, tools: Optional[List] = None):
        self.config = config
        self.client = OpenAI()
        self.tools = tools or []
        self.name = "Solver"
    
    def solve(self, question: str, context: str = "") -> SolverResponse:
        """
        Generate a solution to the given question.
        
        Args:
            question: The problem to solve
            context: Additional context or background information
            
        Returns:
            SolverResponse with structured solution
        """
        start_time = time.time()
        
        # Prepare the prompt
        prompt = get_solver_prompt(question, context)
        
        # Make the API call
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Please solve this problem: {question}"}
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            raw_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            latency_ms = (time.time() - start_time) * 1000
            
            # Parse the response into structured format
            parsed_response = self._parse_response(raw_response)
            
            # Log the interaction
            logger.log_agent_interaction(
                agent_type=self.name,
                input_prompt=prompt,
                output=raw_response,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                confidence=parsed_response.confidence,
                metadata={
                    "question": question,
                    "context_length": len(context),
                    "tools_available": len(self.tools)
                }
            )
            
            return parsed_response
            
        except Exception as e:
            # Log the error and return a fallback response
            logger.log_agent_interaction(
                agent_type=self.name,
                input_prompt=prompt,
                output=f"ERROR: {str(e)}",
                tokens_used=0,
                latency_ms=(time.time() - start_time) * 1000,
                confidence=0.0,
                metadata={"error": str(e)}
            )
            
            return SolverResponse(
                answer=f"I encountered an error while solving this problem: {str(e)}",
                reasoning="Unable to process due to technical error",
                evidence="No evidence available due to error",
                confidence=0.0,
                assumptions="Error occurred during processing"
            )
    
    def _parse_response(self, raw_response: str) -> SolverResponse:
        """
        Parse the raw LLM response into structured format.
        
        This method attempts to extract structured information from the
        free-form response, with fallbacks for missing sections.
        """
        # Initialize default values
        answer = ""
        reasoning = ""
        evidence = ""
        confidence = 0.5  # Default moderate confidence
        assumptions = ""
        tool_calls = []
        
        # Split response into sections
        sections = self._extract_sections(raw_response)
        
        # Extract each section
        answer = sections.get("answer", raw_response[:500] + "..." if len(raw_response) > 500 else raw_response)
        reasoning = sections.get("reasoning", "No explicit reasoning provided")
        evidence = sections.get("evidence", "No evidence cited")
        assumptions = sections.get("assumptions", "No assumptions stated")
        
        # Extract confidence if mentioned
        confidence_text = sections.get("confidence", "0.5")
        try:
            confidence = float(confidence_text.strip().replace("confidence:", "").strip())
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0,1]
        except:
            confidence = 0.5
        
        return SolverResponse(
            answer=answer,
            reasoning=reasoning,
            evidence=evidence,
            confidence=confidence,
            assumptions=assumptions,
            tool_calls=tool_calls
        )
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from formatted response text."""
        sections = {}
        current_section = None
        current_content = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check for section headers (markdown style)
            if line.startswith('**') and line.endswith('**'):
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = line.strip('*').lower().replace(':', '').strip()
                current_content = []
            
            # Check for section headers (colon style)
            elif ':' in line and len(line.split(':')) == 2:
                header, content = line.split(':', 1)
                if header.lower().strip() in ['answer', 'reasoning', 'evidence', 'confidence', 'assumptions']:
                    # Save previous section
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    
                    # Start new section with immediate content
                    current_section = header.lower().strip()
                    current_content = [content.strip()] if content.strip() else []
                else:
                    current_content.append(line)
            else:
                current_content.append(line)
        
        # Save final section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def solve_with_tools(self, question: str, context: str = "") -> SolverResponse:
        """
        Solve a problem with access to tools (placeholder for future implementation).
        
        This method would integrate with the tool layer to perform web searches,
        database queries, or other external operations as needed.
        """
        # For now, delegate to regular solve method
        # In a full implementation, this would:
        # 1. Analyze if tools are needed
        # 2. Call appropriate tools
        # 3. Incorporate tool results into the solution
        
        return self.solve(question, context)