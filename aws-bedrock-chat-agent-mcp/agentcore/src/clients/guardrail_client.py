"""
AWS Bedrock Guardrails Client
Validates content against safety policies
"""

import os
import json
import logging
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class GuardrailClient:
    """Client for interacting with AWS Bedrock Guardrails."""
    
    def __init__(self, region, guardrail_id, guardrail_version):
        """Initialize Guardrail client."""
        self.region = region
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        
        if not self.guardrail_id:
            logger.warning("GUARDRAIL_ID not set. Guardrails will be disabled.")
        
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region
        )
        
        logger.info(f"Initialized Guardrail client with ID: {self.guardrail_id}")
    
    def check_health(self) -> bool:
        """Check if Guardrail service is accessible."""
        if not self.guardrail_id:
            return True  # Skip health check if guardrails disabled
        
        try:
            # Try to get guardrail details as a health check
            bedrock = boto3.client("bedrock", region_name=self.region)
            bedrock.get_guardrail(
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version
            )
            return True
        except Exception as e:
            logger.error(f"Guardrail health check failed: {str(e)}")
            raise
    
    async def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Validate a prompt against guardrail policies.
        
        Args:
            prompt: The text prompt to validate
            
        Returns:
            Dictionary with validation result:
            {
                "approved": bool,
                "reason": str (if blocked),
                "action": str (if blocked),
                "message": str (user-friendly message)
            }
        """
        # If guardrails not configured, approve by default
        if not self.guardrail_id:
            logger.warning("Guardrails not configured, approving by default")
            return {
                "approved": True,
                "message": "Guardrails not configured"
            }
        
        try:
            logger.debug(f"Validating prompt with guardrail {self.guardrail_id}, version {self.guardrail_version}")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            # Call Bedrock Guardrails API
            response = self.bedrock_runtime.apply_guardrail(
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version,
                source="INPUT",
                content=[
                    {
                        "text": {
                            "text": prompt
                        }
                    }
                ]
            )
            
            logger.debug(f"Guardrail response: {json.dumps(response, default=str)}")
            
            # Parse response
            action = response.get("action", "NONE")
            
            if action == "GUARDRAIL_INTERVENED":
                # Content was blocked
                assessments = response.get("assessments", [])
                outputs = response.get("outputs", [])
                
                # Extract block reasons
                reasons = []
                for assessment in assessments:
                    if "topicPolicy" in assessment:
                        for topic in assessment["topicPolicy"].get("topics", []):
                            if topic.get("action") == "BLOCKED":
                                reasons.append(f"Topic: {topic.get('name')}")
                    
                    if "contentPolicy" in assessment:
                        for filter_item in assessment["contentPolicy"].get("filters", []):
                            if filter_item.get("action") == "BLOCKED":
                                filter_type = filter_item.get("type")
                                confidence = filter_item.get("confidence")
                                reasons.append(f"Content filter: {filter_type} ({confidence})")
                
                reason_text = "; ".join(reasons) if reasons else "Content policy violation"
                
                logger.warning(f"Prompt blocked by guardrail: {reason_text}")
                
                return {
                    "approved": False,
                    "reason": reason_text,
                    "action": action,
                    "message": "I cannot generate images with violent, adult, or obscene content. Please provide a different request."
                }
            
            else:
                # Content approved
                logger.info("Prompt approved by guardrail")
                return {
                    "approved": True,
                    "action": action,
                    "message": "Content approved"
                }
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Guardrail API error: {error_code} - {error_message}")
            
            # On error, fail closed (reject the request)
            return {
                "approved": False,
                "reason": f"Guardrail service error: {error_code}",
                "action": "ERROR",
                "message": "Unable to validate content at this time. Please try again later."
            }
        
        except Exception as e:
            logger.error(f"Error validating prompt: {str(e)}")
            
            # On error, fail closed (reject the request)
            return {
                "approved": False,
                "reason": f"Validation error: {str(e)}",
                "action": "ERROR",
                "message": "Unable to validate content at this time. Please try again later."
            }
    
    async def validate_output(self, content: str) -> Dict[str, Any]:
        """
        Validate generated content against guardrail policies.
        
        This can be used to validate image descriptions or other outputs.
        
        Args:
            content: The content to validate
            
        Returns:
            Dictionary with validation result
        """
        if not self.guardrail_id:
            return {
                "approved": True,
                "message": "Guardrails not configured"
            }
        
        try:
            response = self.bedrock_runtime.apply_guardrail(
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version,
                source="OUTPUT",
                content=[
                    {
                        "text": {
                            "text": content
                        }
                    }
                ]
            )
            
            action = response.get("action", "NONE")
            
            if action == "GUARDRAIL_INTERVENED":
                logger.warning("Output blocked by guardrail")
                return {
                    "approved": False,
                    "action": action,
                    "message": "The generated content was blocked due to safety concerns."
                }
            else:
                return {
                    "approved": True,
                    "action": action,
                    "message": "Content approved"
                }
        
        except Exception as e:
            logger.error(f"Error validating output: {str(e)}")
            return {
                "approved": False,
                "reason": str(e),
                "action": "ERROR",
                "message": "Unable to validate content at this time."
            }
