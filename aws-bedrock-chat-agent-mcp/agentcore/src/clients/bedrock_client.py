"""
AWS Bedrock Client for Image Generation
Supports Stability AI and Amazon Titan models
- Model IDs are loaded from Secrets Manager (via provided secrets dict)
- Adds fallback generation: if primary model fails, auto-tries the other model once
"""

import json
import base64
import logging
from typing import Dict, Any, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for interacting with AWS Bedrock image generation models."""

    # Supported model keys in this app
    SUPPORTED_MODELS = ("stability", "titan")

    def __init__(self, region: str, secrets: Dict[str, Any]):
        """
        Initialize Bedrock client.

        Secrets expected (recommended keys):
          - STABILITY_MODEL_ID
          - TITAN_MODEL_ID

        Optionally you can store a nested object, e.g.:
          BEDROCK_IMAGE_MODELS = {"stability": "...", "titan": "..."}
        """
        self.region = region
        self.secrets = secrets or {}

        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region
        )

        # Load model IDs from secrets (no hardcoding)
        self.models = self._load_model_ids(self.secrets)

        logger.info("Initialized Bedrock client in region %s with models=%s",
                    self.region, {k: v for k, v in self.models.items()})

    def _load_model_ids(self, secrets: Dict[str, Any]) -> Dict[str, str]:
        """
        Load model IDs from secrets in a flexible way.
        Priority:
          1) BEDROCK_IMAGE_MODELS dict with keys: stability/titan
          2) STABILITY_MODEL_ID / TITAN_MODEL_ID
        """

        stability_id = (secrets.get("BEDROCK_STABILITY_MODEL") or "").strip()
        titan_id = (secrets.get("BEDROCK_TITAN_MODEL") or "").strip()

        missing = [name for name, mid in [("stability", stability_id), ("titan", titan_id)] if not mid]
        if missing:
            raise ValueError(
                f"Missing Bedrock model IDs in secrets for: {missing}. "
                f"Provide BEDROCK_IMAGE_MODELS={{'stability':..., 'titan':...}} "
                f"or STABILITY_MODEL_ID and TITAN_MODEL_ID."
            )

        return {"stability": stability_id, "titan": titan_id}

    def check_health(self) -> bool:
        """Check if Bedrock service is accessible."""
        try:
            bedrock = boto3.client("bedrock", region_name=self.region)
            # Any provider is fine; this is just a connectivity check
            bedrock.list_foundation_models(maxResults=1)
            return True
        except Exception as e:
            logger.error("Bedrock health check failed: %s", str(e))
            raise

    def _other_model(self, model: str) -> str:
        if model == "titan":
            return "stability"
        if model == "stability":
            return "titan"
        # fallback default
        return "titan"

    async def generate_image(
        self,
        prompt: str,
        model: str = "titan",
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
        cfg_scale: float = 7.0,
        steps: int = 50
    ) -> bytes:
        """
        Generate an image using Bedrock models with fallback.

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

        Flow:
          - Try requested model first
          - If it fails (ClientError or other), log and try the other model once
          - If fallback fails too, raise the fallback exception (with context)
        """
        model = (model or "").strip().lower()
        if model not in self.models:
            raise ValueError(f"Unsupported model: {model}. Choose from {list(self.models.keys())}")

        primary = model
        secondary = self._other_model(primary)

        # First attempt
        try:
            return await self._generate_with_model(
                primary, prompt, width, height, style, cfg_scale, steps
            )
        except Exception as e1:
            logger.warning(
                "Primary image generation failed. primary=%s secondary=%s error=%s",
                primary, secondary, repr(e1)
            )

            # Fallback attempt
            try:
                return await self._generate_with_model(
                    secondary, prompt, width, height, style, cfg_scale, steps
                )
            except Exception as e2:
                logger.error(
                    "Fallback image generation also failed. primary=%s secondary=%s primary_error=%s fallback_error=%s",
                    primary, secondary, repr(e1), repr(e2)
                )
                # Raise the fallback error but include primary context
                raise Exception(
                    f"Image generation failed on both models. "
                    f"primary={primary} error={str(e1)} | fallback={secondary} error={str(e2)}"
                ) from e2

    async def _generate_with_model(
        self,
        model: str,
        prompt: str,
        width: int,
        height: int,
        style: Optional[str],
        cfg_scale: float,
        steps: int
    ) -> bytes:
        model_id = self.models[model]
        logger.info("Generating image with model=%s model_id=%s size=%sx%s",
                    model, model_id, width, height)

        try:
            if model == "stability":
                image_data = await self._generate_stability(prompt, width, height, style, cfg_scale, steps)
            elif model == "titan":
                image_data = await self._generate_titan(prompt, width, height, cfg_scale)
            else:
                raise ValueError(f"Model {model} not implemented")

            logger.info("Successfully generated image with %s, bytes=%s", model, len(image_data))
            return image_data

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error("Bedrock API error model=%s code=%s message=%s", model, error_code, error_message)
            raise Exception(f"Bedrock invoke failed for {model}: {error_code} - {error_message}") from e
        except Exception as e:
            logger.error("Error generating image model=%s: %s", model, str(e))
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
        """Generate image using Stability AI."""
        body = {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": cfg_scale,
            "steps": steps,
            "width": width,
            "height": height,
            "samples": 1
        }
        if style:
            body["style_preset"] = style

        model_id = self.models["stability"]
        logger.debug("Stability request: %s", json.dumps(body))

        response = self.bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())

        if "artifacts" in response_body and response_body["artifacts"]:
            base64_image = response_body["artifacts"][0]["base64"]
            return base64.b64decode(base64_image)

        raise Exception("Stability response did not contain artifacts/base64 image")

    async def _generate_titan(
        self,
        prompt: str,
        width: int,
        height: int,
        cfg_scale: float
    ) -> bytes:
        """Generate image using Amazon Titan."""
        body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": prompt},
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "premium",
                "height": height,
                "width": width,
                "cfgScale": cfg_scale
            }
        }

        model_id = self.models["titan"]
        logger.debug("Titan request: %s", json.dumps(body))

        response = self.bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())

        if "images" in response_body and response_body["images"]:
            return base64.b64decode(response_body["images"][0])

        raise Exception("Titan response did not contain images/base64 image")