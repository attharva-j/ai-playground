"""
Critic Agent - Reviews and critiques solver outputs in the multi-agent system.
"""

import time
import re
from typing import Dict, Any, List
from openai import OpenAI
from pydantic import BaseModel
from enum import Enum

from utils.config import AgentConfig
from utils.prompts import get_critic_prompt
from utils.logger import logger

class CriticDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"

class CriticResponse(BaseModel):
    """Structured response from the Critic Agent."""
    status: CriticDecision
    issues: List[str]
    suggestions: List[str]
    missing: List[str]
    confidence: float
    detailed_feedback: str

class CriticAgent:
    """
    Critic Agent responsible for reviewing and improving solver outputs.
    
    This agent analyzes solutions for accuracy, completeness, logical consistency,
    and evidence quality, providing constructive feedback for improvements.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = OpenAI()
        self.name = "Critic"
    
    def critique(self, question: str, solver_response: str, context: str = "") -> CriticResponse:
        """
        Critique a solver's response and provide feedback.
        
        Args:
            question: The original question being solved
            solver_response: The solver's response to critique
            context: Additional context or background information
            
        Returns:
            CriticResponse with structured critique and feedback
        """
        start_time = time.time()
        
        # Prepare the prompt
        prompt = get_critic_prompt(question, solver_response, context)
        
        # Make the API call
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Please evaluate this response and provide your critique."}
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
                    "solver_response_length": len(solver_response),
                    "decision": parsed_response.status.value,
                    "issues_found": len(parsed_response.issues)
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
            
            return CriticResponse(
                status=CriticDecision.REJECT,
                issues=[f"Technical error during critique: {str(e)}"],
                suggestions=["Please retry the critique process"],
                missing=["Unable to complete analysis due to error"],
                confidence=0.0,
                detailed_feedback=f"Critique failed due to error: {str(e)}"
            )
    
    def _parse_response(self, raw_response: str) -> CriticResponse:
        """
        Parse the raw LLM response into structured format.
        IMPROVED VERSION - More robust status detection
        """
        # Initialize default values
        status = CriticDecision.REJECT  # Default to reject for safety
        issues = []
        suggestions = []
        missing = []
        confidence = 0.5
        detailed_feedback = raw_response
        
        # Extract sections from the response
        sections = self._extract_sections(raw_response)
        
        # Convert response to uppercase for case-insensitive matching
        response_upper = raw_response.upper()
        
        # More robust status detection - check the entire response
        # Look for clear approval signals
        approval_patterns = [
            r'STATUS[:\s]*APPROVE',
            r'DECISION[:\s]*APPROVE',
            r'STATUS[:\s]*IS[:\s]*APPROVE',
            r'\bAPPROVE\b.*RESPONSE',
            r'RESPONSE.*\bAPPROVE\b',
        ]
        
        rejection_patterns = [
            r'STATUS[:\s]*REJECT',
            r'DECISION[:\s]*REJECT',
            r'STATUS[:\s]*IS[:\s]*REJECT',
            r'\bREJECT\b.*RESPONSE',
            r'RESPONSE.*\bREJECT\b',
        ]
        
        # Check for explicit approval/rejection
        has_approval = any(re.search(pattern, response_upper) for pattern in approval_patterns)
        has_rejection = any(re.search(pattern, response_upper) for pattern in rejection_patterns)
        
        # Parse lists (issues, suggestions, missing)
        issues = self._parse_list_section(sections.get("issues", ""))
        suggestions = self._parse_list_section(sections.get("suggestions", ""))
        missing = self._parse_list_section(sections.get("missing", ""))
        
        # Filter out "None", "N/A", empty items
        issues = [i for i in issues if i and i.lower() not in ['none', 'n/a', 'no issues', 'no issues found']]
        suggestions = [s for s in suggestions if s and s.lower() not in ['none', 'n/a', 'no suggestions']]
        missing = [m for m in missing if m and m.lower() not in ['none', 'n/a', 'nothing missing']]
        
        # Decision logic (IMPROVED)
        if has_approval and not has_rejection:
            # Clear approval signal
            status = CriticDecision.APPROVE
        elif has_rejection and not has_approval:
            # Clear rejection signal
            status = CriticDecision.REJECT
        elif not issues and not suggestions and not missing:
            # No issues found at all - should approve
            # Check for positive language in the response
            positive_indicators = [
                'ACCEPTABLE', 'CORRECT', 'ACCURATE', 'GOOD', 'SOUND',
                'WELL-REASONED', 'COMPLETE', 'THOROUGH', 'VALID', 'SATISFACTORY'
            ]
            if any(indicator in response_upper for indicator in positive_indicators):
                status = CriticDecision.APPROVE
            else:
                # If no clear signal and no issues, default to approve
                status = CriticDecision.APPROVE
        else:
            # Has issues - reject
            status = CriticDecision.REJECT
        
        # Parse confidence
        confidence_text = sections.get("confidence", "0.5")
        try:
            # Remove any text before/after the number
            confidence_match = re.search(r'0?\.\d+|1\.0|1(?:\.0+)?|0(?:\.0+)?', confidence_text)
            if confidence_match:
                confidence = float(confidence_match.group())
                confidence = max(0.0, min(1.0, confidence))
            else:
                confidence = 0.5
        except:
            confidence = 0.5
        
        return CriticResponse(
            status=status,
            issues=issues,
            suggestions=suggestions,
            missing=missing,
            confidence=confidence,
            detailed_feedback=detailed_feedback
        )
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from formatted response text."""
        import re
        
        sections = {}
        current_section = None
        current_content = []
        
        lines = text.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Check if this line contains a section header
            # Pattern: optional bullet/number + optional ** + header name + **? + :
            # Examples: "**Answer**:", "- **Reasoning**:", "* **Evidence**:", "1. **Confidence**:"
            header_match = re.match(
                r'^[\-\*•\d.]*\s*\*{0,2}\s*([A-Za-z_]+)\s*\*{0,2}\s*:\s*(.*)',
                line_stripped
            )
            
            if header_match:
                header_name = header_match.group(1).lower().strip()
                header_content = header_match.group(2).strip()
                
                # Check if this is a known section header
                # Agent-specific headers:
                # Solver: answer, reasoning, evidence, confidence, assumptions
                # Critic: status, issues, suggestions, missing, confidence
                # Judge: decision, confidence, reasoning, evidence_quality, concerns
                known_headers = [
                    'answer', 'reasoning', 'evidence', 'confidence', 'assumptions',
                    'status', 'issues', 'suggestions', 'missing',
                    'decision', 'evidence_quality', 'concerns'
                ]
                
                if header_name in known_headers:
                    # Save previous section
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    
                    # Start new section
                    current_section = header_name.replace(' ', '_')
                    current_content = [header_content] if header_content else []
                else:
                    # Not a known header, add to current content
                    if current_section is not None:
                        current_content.append(line_stripped)
            else:
                # Not a header line, add to current content
                if current_section is not None:
                    current_content.append(line_stripped)
        
        # Save final section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _parse_list_section(self, text: str) -> List[str]:
        """Parse a text section into a list of items."""
        if not text:
            return []
        
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove bullet points and numbering
            if line.startswith(('- ', '* ', '• ')):
                line = line[2:].strip()
            elif line.startswith(tuple(f"{i}. " for i in range(1, 10))):
                line = line.split('. ', 1)[1].strip() if '. ' in line else line
            
            if line:
                items.append(line)
        
        return items
    
    def get_improvement_priority(self, critique: CriticResponse) -> str:
        """
        Determine the priority level of improvements needed.
        
        Returns:
            Priority level: "HIGH", "MEDIUM", or "LOW"
        """
        if critique.status == CriticDecision.APPROVE:
            return "LOW"
        
        # High priority if many issues or low confidence
        if len(critique.issues) >= 3 or critique.confidence < 0.3:
            return "HIGH"
        elif len(critique.issues) >= 1 or critique.confidence < 0.6:
            return "MEDIUM"
        else:
            return "LOW"
    
    def generate_revision_guidance(self, critique: CriticResponse) -> str:
        """
        Generate specific guidance for revising the solution based on critique.
        
        Returns:
            Formatted revision guidance string
        """
        if critique.status == CriticDecision.APPROVE:
            return "No revisions needed. The solution is acceptable."
        
        guidance = "Revision Guidance:\n\n"
        
        if critique.issues:
            guidance += "Issues to Address:\n"
            for i, issue in enumerate(critique.issues, 1):
                guidance += f"{i}. {issue}\n"
            guidance += "\n"
        
        if critique.suggestions:
            guidance += "Suggested Improvements:\n"
            for i, suggestion in enumerate(critique.suggestions, 1):
                guidance += f"{i}. {suggestion}\n"
            guidance += "\n"
        
        if critique.missing:
            guidance += "Missing Information to Add:\n"
            for i, missing in enumerate(critique.missing, 1):
                guidance += f"{i}. {missing}\n"
            guidance += "\n"
        
        priority = self.get_improvement_priority(critique)
        guidance += f"Priority Level: {priority}\n"
        guidance += f"Critic Confidence: {critique.confidence:.2f}\n"
        
        return guidance