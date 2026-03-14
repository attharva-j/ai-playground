"""
Unit tests for MCP Image Generator Server
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["GUARDRAIL_ID"] = "test-guardrail-id"

from src.server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MCP Image Generator"
    assert data["status"] == "healthy"


def test_health_check(client):
    """Test health check endpoint."""
    with patch('src.bedrock_client.BedrockClient.check_health'), \
         patch('src.s3_client.S3Client.check_health'), \
         patch('src.guardrail_client.GuardrailClient.check_health'):
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data


def test_list_tools(client):
    """Test MCP tools list endpoint."""
    response = client.post("/mcp/tools/list")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert len(data["tools"]) > 0
    assert data["tools"][0]["name"] == "generate_image"


@pytest.mark.asyncio
async def test_generate_image_success():
    """Test successful image generation."""
    from src.server import generate_image, ImageGenerationRequest
    
    # Mock all external dependencies
    with patch('src.guardrail_client.GuardrailClient.validate_prompt') as mock_guardrail, \
         patch('src.bedrock_client.BedrockClient.generate_image') as mock_bedrock, \
         patch('src.s3_client.S3Client.upload_image') as mock_s3_upload, \
         patch('src.s3_client.S3Client.generate_presigned_url') as mock_s3_url:
        
        # Setup mocks
        mock_guardrail.return_value = {"approved": True}
        mock_bedrock.return_value = b"fake_image_data"
        mock_s3_upload.return_value = {"key": "test-key", "bucket": "test-bucket", "size": 1024}
        mock_s3_url.return_value = "https://test-bucket.s3.amazonaws.com/test-key"
        
        # Create request
        request = ImageGenerationRequest(
            prompt="A beautiful sunset",
            model="stability"
        )
        
        # Execute
        response = await generate_image(request)
        
        # Verify
        assert response.success is True
        assert response.image_url is not None
        assert response.model_used == "stability"


@pytest.mark.asyncio
async def test_generate_image_blocked_by_guardrail():
    """Test image generation blocked by guardrail."""
    from src.server import generate_image, ImageGenerationRequest
    
    with patch('src.guardrail_client.GuardrailClient.validate_prompt') as mock_guardrail:
        # Setup mock to block content
        mock_guardrail.return_value = {
            "approved": False,
            "message": "Content blocked"
        }
        
        # Create request with inappropriate content
        request = ImageGenerationRequest(
            prompt="violent content",
            model="stability"
        )
        
        # Execute
        response = await generate_image(request)
        
        # Verify
        assert response.success is False
        assert response.error == "Content blocked by guardrail"


def test_generate_image_invalid_model(client):
    """Test image generation with invalid model."""
    response = client.post("/generate", json={
        "prompt": "A sunset",
        "model": "invalid_model"
    })
    
    # Should still accept the request but may fail during generation
    assert response.status_code in [200, 422]


def test_generate_image_missing_prompt(client):
    """Test image generation without prompt."""
    response = client.post("/generate", json={
        "model": "stability"
    })
    
    # Should return validation error
    assert response.status_code == 422


def test_mcp_call_tool_success(client):
    """Test MCP tool call endpoint."""
    with patch('src.guardrail_client.GuardrailClient.validate_prompt') as mock_guardrail, \
         patch('src.bedrock_client.BedrockClient.generate_image') as mock_bedrock, \
         patch('src.s3_client.S3Client.upload_image') as mock_s3_upload, \
         patch('src.s3_client.S3Client.generate_presigned_url') as mock_s3_url:
        
        # Setup mocks
        mock_guardrail.return_value = {"approved": True}
        mock_bedrock.return_value = b"fake_image_data"
        mock_s3_upload.return_value = {"key": "test-key", "bucket": "test-bucket", "size": 1024}
        mock_s3_url.return_value = "https://test-bucket.s3.amazonaws.com/test-key"
        
        response = client.post("/mcp/tools/call", json={
            "name": "generate_image",
            "arguments": {
                "prompt": "A sunset",
                "model": "stability"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data


def test_mcp_call_tool_not_found(client):
    """Test MCP tool call with invalid tool name."""
    response = client.post("/mcp/tools/call", json={
        "name": "invalid_tool",
        "arguments": {}
    })
    
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
