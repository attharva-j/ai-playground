"""
Judge Agent - Final validation agent in the multi-agent system.
FIXED VERSION - Improved parsing to prevent always failing responses
"""

import time
import re
from typing import Dict, Any, List
from openai import OpenAI
from pydantic import BaseModel
from enum import Enum

from utils.config import AgentConfig
from utils.prompts import get_judge_prompt
from utils.logger import logger

class JudgeDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"

class EvidenceQuality(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"

class JudgeResponse(BaseModel):
    """Structured response from the Judge Agent."""
    decision: JudgeDecision
    confidence: float
    reasoning: str
    evidence_quality: EvidenceQuality
    concerns: List[str]
    validation_score: float  # 0.0 to 1.0

class JudgeAgent:
    """
    Judge Agent responsible for final validation of solutions.
    
    This agent makes the final pass/fail decision on solutions, focusing on
    factual accuracy, evidence quality, and overall solution completeness.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = OpenAI()
        self.name = "Judge"
    
    def validate(self, question: str, final_response: str, context: str = "") -> JudgeResponse:
        """
        Validate a final response and make a pass/fail decision.
        
        Args:
            question: The original question being solved
            final_response: The final response to validate
            context: Additional context or background information
            
        Returns:
            JudgeResponse with validation decision and details
        """
        start_time = time.time()
        
        # Prepare the prompt
        prompt = get_judge_prompt(question, final_response, context)
        
        # Make the API call
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Please make your final validation decision."}
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            raw_response = response.choices[0].message.content
            print(f"Judge's raw response:\n{raw_response}")

            tokens_used = response.usage.total_tokens if response.usage else 0
            latency_ms = (time.time() - start_time) * 1000
            
            # Parse the response into structured format
            parsed_response = self._parse_response(raw_response)
            print(f"Parsed response:\n{parsed_response}")

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
                    "response_length": len(final_response),
                    "decision": parsed_response.decision.value,
                    "evidence_quality": parsed_response.evidence_quality.value,
                    "validation_score": parsed_response.validation_score,
                    "concerns_count": len(parsed_response.concerns)
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
            
            return JudgeResponse(
                decision=JudgeDecision.FAIL,
                confidence=0.0,
                reasoning=f"Validation failed due to technical error: {str(e)}",
                evidence_quality=EvidenceQuality.WEAK,
                concerns=[f"Technical error during validation: {str(e)}"],
                validation_score=0.0
            )
    
    def _parse_response(self, raw_response: str) -> JudgeResponse:
        """
        Parse the raw LLM response into structured format.
        IMPROVED VERSION - More robust decision detection
        """
        # Initialize default values
        decision = JudgeDecision.FAIL  # Default to fail for safety
        confidence = 0.5  # Changed from 0.0 to 0.5 for more balanced default
        reasoning = raw_response
        evidence_quality = EvidenceQuality.MODERATE  # Changed from WEAK to MODERATE for more balanced default
        concerns = []
        validation_score = 0.0
        
        # Extract sections from the response
        sections = self._extract_sections(raw_response)
        
        # Convert response to uppercase for case-insensitive matching
        response_upper = raw_response.upper()
        
        # More robust decision detection - check the entire response
        # Look for clear pass/fail signals
        pass_patterns = [
            r'DECISION[:\s]*PASS',
            r'DECISION[:\s]*IS[:\s]*PASS',
            r'\bPASS\b.*VALIDATION',
            r'VALIDATION.*\bPASS\b',
            r'STATUS[:\s]*PASS',
            r'SHOULD.*\bPASS\b',
        ]
        
        fail_patterns = [
            r'DECISION[:\s]*FAIL',
            r'DECISION[:\s]*IS[:\s]*FAIL',
            r'\bFAIL\b.*VALIDATION',
            r'VALIDATION.*\bFAIL\b',
            r'STATUS[:\s]*FAIL',
            r'SHOULD.*\bFAIL\b',
        ]
        
        # Check for explicit pass/fail signals
        has_pass = any(re.search(pattern, response_upper) for pattern in pass_patterns)
        has_fail = any(re.search(pattern, response_upper) for pattern in fail_patterns)
        
        # Parse concerns
        concerns = self._parse_list_section(sections.get("concerns", ""))
        
        # Filter out "None", "N/A", empty items from concerns
        concerns = [c for c in concerns if c and c.lower() not in ['none', 'n/a', 'no concerns', 'no concerns found', 'no issues']]
        
        # Decision logic (IMPROVED)
        if has_pass and not has_fail:
            # Clear pass signal
            decision = JudgeDecision.PASS
        elif has_fail and not has_pass:
            # Clear fail signal
            decision = JudgeDecision.FAIL
        elif not concerns:
            # No concerns found at all - should pass
            # Check for positive language in the response
            positive_indicators = [
                'ACCURATE', 'CORRECT', 'VALID', 'SOUND', 'ACCEPTABLE',
                'WELL-SUPPORTED', 'VERIFIED', 'CONFIRMED', 'RELIABLE', 'TRUSTWORTHY'
            ]
            if any(indicator in response_upper for indicator in positive_indicators):
                decision = JudgeDecision.PASS
            else:
                # If no clear signal and no concerns, lean toward pass
                # (being less conservative than before)
                decision = JudgeDecision.PASS
        else:
            # Has concerns - fail
            decision = JudgeDecision.FAIL
        
        # Parse confidence
        confidence_text = sections.get("confidence", "0.5")
        try:
            # Remove any text before/after the number using regex
            confidence_match = re.search(r'0?\.\d+|1\.0|1(?:\.0+)?|0(?:\.0+)?', confidence_text)
            if confidence_match:
                confidence = float(confidence_match.group())
                confidence = max(0.0, min(1.0, confidence))
            else:
                confidence = 0.5
        except:
            confidence = 0.5
        
        # Parse reasoning
        reasoning = sections.get("reasoning", raw_response)
        if not reasoning or len(reasoning.strip()) < 10:
            reasoning = "No explicit reasoning provided"
        
        # Parse evidence quality - more robust extraction
        evidence_text = sections.get("evidence_quality", "").upper().strip()
        
        # Check for evidence quality in the entire response if not found in section
        if not evidence_text or len(evidence_text) < 3:
            evidence_text = response_upper
        
        # Use regex patterns for more robust matching
        if re.search(r'\bSTRONG\b', evidence_text):
            evidence_quality = EvidenceQuality.STRONG
        elif re.search(r'\bMODERATE\b', evidence_text):
            evidence_quality = EvidenceQuality.MODERATE
        elif re.search(r'\bWEAK\b', evidence_text):
            evidence_quality = EvidenceQuality.WEAK
        else:
            # Default based on decision
            if decision == JudgeDecision.PASS:
                evidence_quality = EvidenceQuality.MODERATE
            else:
                evidence_quality = EvidenceQuality.WEAK
        
        # Calculate validation score based on decision, confidence, and evidence quality
        validation_score = self._calculate_validation_score(decision, confidence, evidence_quality, concerns)
        
        return JudgeResponse(
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            evidence_quality=evidence_quality,
            concerns=concerns,
            validation_score=validation_score
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
    
    def _calculate_validation_score(
        self, 
        decision: JudgeDecision, 
        confidence: float, 
        evidence_quality: EvidenceQuality, 
        concerns: List[str]
    ) -> float:
        """
        Calculate a numerical validation score based on judge assessment.
        
        Returns:
            Score from 0.0 to 1.0
        """
        base_score = 0.0
        
        # Base score from decision
        if decision == JudgeDecision.PASS:
            base_score = 0.7
        else:
            base_score = 0.2
        
        # Adjust for confidence
        confidence_adjustment = confidence * 0.2
        
        # Adjust for evidence quality
        evidence_adjustment = 0.0
        if evidence_quality == EvidenceQuality.STRONG:
            evidence_adjustment = 0.1
        elif evidence_quality == EvidenceQuality.MODERATE:
            evidence_adjustment = 0.05
        # WEAK gets no adjustment (0.0)
        
        # Penalize for concerns
        concern_penalty = min(len(concerns) * 0.05, 0.2)
        
        # Calculate final score
        final_score = base_score + confidence_adjustment + evidence_adjustment - concern_penalty
        
        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, final_score))
    
    def should_accept(self, judge_response: JudgeResponse, threshold: float = 0.8) -> bool:
        """
        Determine if the response should be accepted based on judge assessment.
        
        Args:
            judge_response: The judge's assessment
            threshold: Minimum confidence threshold for acceptance
            
        Returns:
            True if response should be accepted, False otherwise
        """
        return (
            judge_response.decision == JudgeDecision.PASS and
            judge_response.confidence >= threshold and
            judge_response.validation_score >= threshold
        )
    
    def get_rejection_reason(self, judge_response: JudgeResponse) -> str:
        """
        Get a human-readable reason for rejection.
        
        Returns:
            Formatted rejection reason
        """
        if judge_response.decision == JudgeDecision.PASS:
            return "Response was not rejected"
        
        reasons = []
        
        if judge_response.confidence < 0.5:
            reasons.append(f"Low confidence ({judge_response.confidence:.2f})")
        
        if judge_response.evidence_quality == EvidenceQuality.WEAK:
            reasons.append("Weak evidence quality")
        
        if judge_response.concerns:
            reasons.append(f"{len(judge_response.concerns)} concerns identified")
        
        if judge_response.validation_score < 0.5:
            reasons.append(f"Low validation score ({judge_response.validation_score:.2f})")
        
        if not reasons:
            reasons.append("Failed general validation criteria")
        
        return "Rejection reasons: " + ", ".join(reasons)