"""
Utility functions for logging, metrics, and helpers
"""

import os
import logging
import json
from datetime import datetime
from typing import Any, Dict

import boto3


def setup_logging() -> logging.Logger:
    """
    Setup structured logging for the application.
    
    Returns:
        Configured logger instance
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger("mcp_image_generator")
    logger.setLevel(getattr(logging, log_level))
    
    # Add structured logging handler for CloudWatch
    if os.getenv("ENABLE_CLOUDWATCH_LOGS", "true").lower() == "true":
        try:
            from pythonjsonlogger import jsonlogger
            
            json_handler = logging.StreamHandler()
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s'
            )
            json_handler.setFormatter(formatter)
            logger.addHandler(json_handler)
        except ImportError:
            logger.warning("python-json-logger not available, using standard logging")
    
    return logger


def log_metric(metric_name: str, value: float, unit: str = "Count") -> None:
    """
    Log a custom metric to CloudWatch.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Metric unit (Count, Seconds, etc.)
    """
    try:
        if os.getenv("ENABLE_CLOUDWATCH_METRICS", "true").lower() != "true":
            return
        
        cloudwatch = boto3.client(
            'cloudwatch',
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        
        cloudwatch.put_metric_data(
            Namespace='MCP/ImageGenerator',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit,
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to log metric {metric_name}: {str(e)}")


def validate_image_dimensions(width: int, height: int) -> tuple:
    """
    Validate and adjust image dimensions to supported values.
    
    Args:
        width: Requested width
        height: Requested height
        
    Returns:
        Tuple of (validated_width, validated_height)
    """
    # Ensure dimensions are within bounds
    min_dim = 512
    max_dim = 2048
    
    width = max(min_dim, min(width, max_dim))
    height = max(min_dim, min(height, max_dim))
    
    # Round to nearest multiple of 64 (required by some models)
    width = (width // 64) * 64
    height = (height // 64) * 64
    
    return width, height


def sanitize_prompt(prompt: str, max_length: int = 1000) -> str:
    """
    Sanitize and truncate prompt text.
    
    Args:
        prompt: Input prompt
        max_length: Maximum allowed length
        
    Returns:
        Sanitized prompt
    """
    # Remove excessive whitespace
    prompt = ' '.join(prompt.split())
    
    # Truncate if too long
    if len(prompt) > max_length:
        prompt = prompt[:max_length]
    
    return prompt


def format_error_response(error: Exception, request_id: str = None) -> Dict[str, Any]:
    """
    Format an error into a standardized response.
    
    Args:
        error: Exception object
        request_id: Optional request ID
        
    Returns:
        Error response dictionary
    """
    response = {
        "success": False,
        "error": type(error).__name__,
        "message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if request_id:
        response["request_id"] = request_id
    
    return response


def get_model_config(model_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Model configuration dictionary
    """
    configs = {
        "stability": {
            "model_id": "stability.stable-diffusion-xl-v1",
            "max_width": 1024,
            "max_height": 1024,
            "default_steps": 50,
            "default_cfg_scale": 7.0,
            "supports_styles": True,
            "styles": [
                "photographic",
                "digital-art",
                "cinematic",
                "anime",
                "3d-model",
                "comic-book",
                "fantasy-art",
                "line-art",
                "analog-film",
                "neon-punk"
            ]
        },
        "titan": {
            "model_id": "amazon.titan-image-generator-v1",
            "max_width": 1024,
            "max_height": 1024,
            "default_cfg_scale": 8.0,
            "supports_styles": False,
            "quality_options": ["standard", "premium"]
        }
    }
    
    return configs.get(model_name, {})


def calculate_cost_estimate(model: str, width: int, height: int) -> float:
    """
    Calculate estimated cost for image generation.
    
    Args:
        model: Model name
        width: Image width
        height: Image height
        
    Returns:
        Estimated cost in USD
    """
    # Approximate pricing (as of 2024)
    pricing = {
        "stability": 0.04,  # per image
        "titan": 0.008      # per image (standard quality)
    }
    
    base_cost = pricing.get(model, 0.04)
    
    # Adjust for resolution (higher resolution = higher cost)
    pixels = width * height
    base_pixels = 1024 * 1024
    resolution_multiplier = pixels / base_pixels
    
    return base_cost * resolution_multiplier


def create_image_metadata(
    prompt: str,
    model: str,
    width: int,
    height: int,
    request_id: str
) -> Dict[str, str]:
    """
    Create metadata dictionary for S3 object.
    
    Args:
        prompt: Generation prompt
        model: Model used
        width: Image width
        height: Image height
        request_id: Request ID
        
    Returns:
        Metadata dictionary
    """
    return {
        "prompt": prompt[:100],  # Truncate for metadata limits
        "model": model,
        "width": str(width),
        "height": str(height),
        "request_id": request_id,
        "generated_at": datetime.utcnow().isoformat(),
        "service": "mcp-image-generator"
    }
