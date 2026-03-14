"""
AWS Bedrock Client for Image Generation
Supports Stability AI and Amazon Titan models
"""

import os
import json
import base64
import logging
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for interacting with AWS Bedrock image generation models."""
    
    def __init__(self):
        """Initialize Bedrock client."""
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region
        )
        
        # Model IDs
        self.models = {
            "stability": "stability.stable-diffusion-xl-v1",
            "titan": "amazon.titan-image-generator-v1"
        }
        
        logger.info(f"Initialized Bedrock client in region {self.region}")
    
    def check_health(self) -> bool:
        """Check if Bedrock service is accessible."""
        try:
            # Try to list foundation models as a health check
            bedrock = boto3.client("bedrock", region_name=self.region)
            bedrock.list_foundation_models(byProvider="Stability AI")
            return True
        except Exception as e:
            logger.error(f"Bedrock health check failed: {str(e)}")
            raise
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "stability",
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
        cfg_scale: float = 7.0,
        steps: int = 50
    ) -> bytes:
        """
        Generate an image using Bedrock models.
        
        Args:
            prompt: Text description of the image
            model: Model to use ('stability' or 'titan')
            width: Image width
            height: Image height
            style: Image style (for Stability AI)
            cfg_scale: CFG scale for generation
            steps: Number of generation steps
            
        Returns:
            Image data as bytes
        """
        if model not in self.models:
            raise ValueError(f"Unsupported model: {model}. Choose from {list(self.models.keys())}")
        
        model_id = self.models[model]
        
        try:
            if model == "stability":
                image_data = await self._generate_stability(
                    prompt, width, height, style, cfg_scale, steps
                )
            elif model == "titan":
                image_data = await self._generate_titan(
                    prompt, width, height, cfg_scale
                )
            else:
                raise ValueError(f"Model {model} not implemented")
            
            logger.info(f"Successfully generated image with {model}")
            return image_data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Bedrock API error: {error_code} - {error_message}")
            raise Exception(f"Failed to generate image: {error_message}")
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            raise
    
    async def _generate_stability(
        self,
        prompt: str,
        width: int,
        height: int,
        style: Optional[str],
        cfg_scale: float,
        steps: int
    ) -> bytes:
        """Generate image using Stability AI SDXL."""
        # Prepare request body for Stability AI
        body = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1.0
                }
            ],
            "cfg_scale": cfg_scale,
            "steps": steps,
            "width": width,
            "height": height,
            "samples": 1
        }
        
        # Add style preset if provided
        if style:
            body["style_preset"] = style
        
        logger.debug(f"Stability AI request: {json.dumps(body, indent=2)}")
        
        # Invoke model
        response = self.bedrock_runtime.invoke_model(
            modelId=self.models["stability"],
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract base64 image
        if "artifacts" in response_body and len(response_body["artifacts"]) > 0:
            base64_image = response_body["artifacts"][0]["base64"]
            image_data = base64.b64decode(base64_image)
            return image_data
        else:
            raise Exception("No image generated in response")
    
    async def _generate_titan(
        self,
        prompt: str,
        width: int,
        height: int,
        cfg_scale: float
    ) -> bytes:
        """Generate image using Amazon Titan."""
        # Prepare request body for Titan
        body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "premium",
                "height": height,
                "width": width,
                "cfgScale": cfg_scale
            }
        }
        
        logger.debug(f"Titan request: {json.dumps(body, indent=2)}")
        
        # Invoke model
        response = self.bedrock_runtime.invoke_model(
            modelId=self.models["titan"],
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract base64 image
        if "images" in response_body and len(response_body["images"]) > 0:
            base64_image = response_body["images"][0]
            image_data = base64.b64decode(base64_image)
            return image_data
        else:
            raise Exception("No image generated in response")
