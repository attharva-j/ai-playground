"""
MCP Server for Image Generation with Guardrails
Hosted on AWS Agentcore Runtime
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from .bedrock_client import BedrockClient
from .guardrail_client import GuardrailClient
from .s3_client import S3Client
from .utils import setup_logging, log_metric

# Setup logging
logger = setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="MCP Image Generator",
    description="MCP server for safe image generation using AWS Bedrock",
    version="1.0.0"
)

# Initialize clients
bedrock_client = BedrockClient()
guardrail_client = GuardrailClient()
s3_client = S3Client()


class ImageGenerationRequest(BaseModel):
    """Request model for image generation."""
    prompt: str = Field(..., description="Description of the image to generate")
    model: str = Field(default="stability", description="Model to use (stability or titan)")
    width: int = Field(default=1024, ge=512, le=2048, description="Image width")
    height: int = Field(default=1024, ge=512, le=2048, description="Image height")
    style: Optional[str] = Field(default=None, description="Image style (for Stability AI)")
    cfg_scale: float = Field(default=7.0, ge=1.0, le=35.0, description="CFG scale")
    steps: int = Field(default=50, ge=10, le=150, description="Generation steps")


class ImageGenerationResponse(BaseModel):
    """Response model for image generation."""
    success: bool
    image_url: Optional[str] = None
    image_id: Optional[str] = None
    model_used: Optional[str] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "MCP Image Generator",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "bedrock": "unknown",
            "s3": "unknown",
            "guardrail": "unknown"
        }
    }
    
    # Check Bedrock connectivity
    try:
        bedrock_client.check_health()
        health_status["services"]["bedrock"] = "healthy"
    except Exception as e:
        health_status["services"]["bedrock"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check S3 connectivity
    try:
        s3_client.check_health()
        health_status["services"]["s3"] = "healthy"
    except Exception as e:
        health_status["services"]["s3"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Guardrail connectivity
    try:
        guardrail_client.check_health()
        health_status["services"]["guardrail"] = "healthy"
    except Exception as e:
        health_status["services"]["guardrail"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


@app.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Generate an image based on the provided prompt.
    
    This endpoint:
    1. Validates the prompt using Bedrock Guardrails
    2. Generates the image using Bedrock models
    3. Uploads the image to S3
    4. Returns a presigned URL
    """
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Received image generation request", extra={
        "request_id": request_id,
        "prompt": request.prompt,
        "model": request.model
    })
    
    try:
        # Step 1: Validate prompt with Guardrails
        logger.info(f"[{request_id}] Validating prompt with guardrails")
        guardrail_result = await guardrail_client.validate_prompt(request.prompt)
        
        if not guardrail_result["approved"]:
            logger.warning(f"[{request_id}] Prompt blocked by guardrail", extra={
                "reason": guardrail_result.get("reason"),
                "action": guardrail_result.get("action")
            })
            log_metric("GuardrailBlocks", 1)
            
            return ImageGenerationResponse(
                success=False,
                error="Content blocked by guardrail",
                message=guardrail_result.get("message", 
                    "I cannot generate images with violent, adult, or obscene content. Please provide a different request.")
            )
        
        logger.info(f"[{request_id}] Prompt approved by guardrail")
        log_metric("GuardrailApprovals", 1)
        
        # Step 2: Generate image with Bedrock
        logger.info(f"[{request_id}] Generating image with {request.model}")
        start_time = datetime.utcnow()
        
        image_data = await bedrock_client.generate_image(
            prompt=request.prompt,
            model=request.model,
            width=request.width,
            height=request.height,
            style=request.style,
            cfg_scale=request.cfg_scale,
            steps=request.steps
        )
        
        generation_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"[{request_id}] Image generated in {generation_time:.2f}s")
        log_metric("ImageGenerationTime", generation_time)
        log_metric("ImagesGenerated", 1)
        
        # Step 3: Upload to S3
        logger.info(f"[{request_id}] Uploading image to S3")
        image_id = str(uuid.uuid4())
        
        s3_result = await s3_client.upload_image(
            image_data=image_data,
            image_id=image_id,
            metadata={
                "request_id": request_id,
                "prompt": request.prompt[:100],  # Truncate for metadata
                "model": request.model,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"[{request_id}] Image uploaded successfully", extra={
            "image_id": image_id,
            "s3_key": s3_result["key"]
        })
        log_metric("S3Uploads", 1)
        
        # Step 4: Generate presigned URL
        presigned_url = await s3_client.generate_presigned_url(
            s3_key=s3_result["key"],
            expiry_seconds=3600  # 1 hour
        )
        
        logger.info(f"[{request_id}] Request completed successfully")
        log_metric("SuccessfulRequests", 1)
        
        return ImageGenerationResponse(
            success=True,
            image_url=presigned_url,
            image_id=image_id,
            model_used=request.model,
            expires_in=3600
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] Error generating image: {str(e)}", exc_info=True)
        log_metric("FailedRequests", 1)
        
        return ImageGenerationResponse(
            success=False,
            error="Internal server error",
            message=f"Failed to generate image: {str(e)}"
        )


@app.post("/mcp/tools/list")
async def list_tools():
    """
    MCP Protocol: List available tools.
    This endpoint is called by MCP clients to discover available tools.
    """
    return {
        "tools": [
            {
                "name": "generate_image",
                "description": "Generate an image based on a text prompt using AWS Bedrock models with content safety guardrails",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Description of the image to generate"
                        },
                        "model": {
                            "type": "string",
                            "description": "Model to use for generation",
                            "enum": ["stability", "titan"],
                            "default": "stability"
                        },
                        "width": {
                            "type": "integer",
                            "description": "Image width in pixels",
                            "minimum": 512,
                            "maximum": 2048,
                            "default": 1024
                        },
                        "height": {
                            "type": "integer",
                            "description": "Image height in pixels",
                            "minimum": 512,
                            "maximum": 2048,
                            "default": 1024
                        },
                        "style": {
                            "type": "string",
                            "description": "Image style (for Stability AI)",
                            "enum": ["photographic", "digital-art", "cinematic", "anime", "3d-model"],
                            "default": "photographic"
                        }
                    },
                    "required": ["prompt"]
                }
            }
        ]
    }


@app.post("/mcp/tools/call")
async def call_tool(request: Request):
    """
    MCP Protocol: Execute a tool.
    This endpoint is called by MCP clients to execute a specific tool.
    """
    body = await request.json()
    tool_name = body.get("name")
    arguments = body.get("arguments", {})
    
    if tool_name == "generate_image":
        # Convert MCP request to internal request format
        image_request = ImageGenerationRequest(
            prompt=arguments.get("prompt"),
            model=arguments.get("model", "stability"),
            width=arguments.get("width", 1024),
            height=arguments.get("height", 1024),
            style=arguments.get("style")
        )
        
        # Generate image
        result = await generate_image(image_request)
        
        # Convert to MCP response format
        if result.success:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Image generated successfully! View it here: {result.image_url}"
                    },
                    {
                        "type": "resource",
                        "resource": {
                            "uri": result.image_url,
                            "mimeType": "image/png",
                            "metadata": {
                                "image_id": result.image_id,
                                "model_used": result.model_used,
                                "expires_in": result.expires_in
                            }
                        }
                    }
                ]
            }
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {result.message}"
                    }
                ],
                "isError": True
            }
    else:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc)
        }
    )


def main():
    """Run the server."""
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting MCP Image Generator server on {host}:{port}")
    
    uvicorn.run(
        "src.server:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
