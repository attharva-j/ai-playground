# schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Description of the image to generate")
    model: str = Field(default="stability", description="stability or titan")
    width: int = Field(default=1024, ge=512, le=2048)
    height: int = Field(default=1024, ge=512, le=2048)
    style: Optional[str] = None
    cfg_scale: float = Field(default=7.0, ge=1.0, le=35.0)
    steps: int = Field(default=50, ge=10, le=150)
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ImageGenerationResult(BaseModel):
    success: bool
    request_id: str
    image_url: Optional[str] = None
    image_id: Optional[str] = None
    model_used: Optional[str] = None
    s3_key: Optional[str] = None
    expires_in: Optional[int] = None
    elapsed_ms: Optional[int] = None
    status: Optional[str] = None
    message: Optional[str] = None
    reason: Optional[str] = None