from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError
from fastmcp import FastMCP, Context

from schemas.image_schemas import ImageGenerationResult
from utils.metric_util import log_metric
from utils.logger_util import log_step

logger = logging.getLogger("mcp_image_generator")


def _ctx(ctx: Context):
    """
    AppContext injected by lifespan() in main.py
    """
    app_ctx = ctx.request_context.lifespan_context
    if app_ctx is None:
        raise RuntimeError(
            "Missing lifespan context. Ensure FastMCP server uses lifespan=app_lifespan "
            "and that requests are routed through the FastMCP server instance."
        )
    return app_ctx


def _audit_put(audit_table, item: Dict[str, Any]) -> None:
    """Best-effort audit write; never fail the tool because audit failed."""
    if not audit_table:
        return
    try:
        audit_table.put_item(Item=item)
    except ClientError:
        logger.exception("audit_put_failed")


def register_image_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def generate_image(
        ctx: Context,
        prompt: str,
        model: str = "stability",
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
        cfg_scale: float = 7.0,
        steps: int = 50,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        MCP Tool: validate prompt with Bedrock Guardrails, generate image with Bedrock,
        upload to S3, return presigned URL, write audit logs to DynamoDB, and emit metrics.
        """
        if not prompt or not prompt.strip():
            raise ValueError("prompt is required")

        app_ctx = _ctx(ctx)

        secrets = app_ctx.secrets
        bedrock_client = app_ctx.bedrock
        guardrail_client = app_ctx.guardrail
        s3_client = app_ctx.s3
        audit_table = app_ctx.audit_table

        rid = request_id or str(uuid.uuid4())
        uid = user_id or "unknown"
        metadata = metadata or {}
        started = time.time()

        log_step(
            logger,
            "REQUEST_START",
            rid,
            uid,
            f"Image generation request started: model={model}, size={width}x{height}",
            prompt=prompt[:100],
            model=model,
            width=width,
            height=height,
        )

        # Metric: request received
        log_metric("ToolRequests", 1)

        # Audit: STARTED
        _audit_put(audit_table, {
            "request_id": rid,
            "ts": datetime.now(timezone.utc).isoformat(),
            "status": "STARTED",
            "user_id": uid,
            "model": model,
            "prompt": prompt[:2000],
            "width": int(width),
            "height": int(height),
        })

        # 1) Guardrails (INPUT)
        log_step(logger, "GUARDRAIL_START", rid, uid, "Starting guardrail validation")

        try:
            guard = await guardrail_client.validate_prompt(prompt)
            log_step(
                logger,
                "GUARDRAIL_COMPLETE",
                rid,
                uid,
                f"Guardrail validation completed: approved={guard.get('approved', False)}",
                approved=guard.get("approved"),
                action=guard.get("action"),
            )
        except Exception as e:
            elapsed_ms = int((time.time() - started) * 1000)
            err = f"{type(e).__name__}: {str(e)}"

            log_step(
                logger,
                "GUARDRAIL_ERROR",
                rid,
                uid,
                f"Guardrail validation failed: {err}",
                level="ERROR",
                error=err,
                elapsed_ms=elapsed_ms,
            )

            log_metric("GuardrailErrors", 1)
            log_metric("ToolFailures", 1)
            log_metric("ToolLatency", elapsed_ms / 1000, unit="Seconds")

            _audit_put(audit_table, {
                "request_id": rid,
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED_GUARDRAIL",
                "user_id": uid,
                "model": model,
                "error": err[:2000],
                "elapsed_ms": elapsed_ms,
            })

            logger.exception("guardrail_validation_failed request_id=%s elapsed_ms=%s", rid, elapsed_ms)
            raise

        if not guard.get("approved", False):
            elapsed_ms = int((time.time() - started) * 1000)
            reason = str(guard.get("reason", "blocked"))[:2000]
            msg = guard.get("message", "Blocked by guardrails")

            log_step(
                logger,
                "GUARDRAIL_BLOCKED",
                rid,
                uid,
                f"Content blocked by guardrails: {reason}",
                level="WARNING",
                reason=reason,
                elapsed_ms=elapsed_ms,
            )

            log_metric("GuardrailBlocks", 1)
            log_metric("ToolBlocked", 1)
            log_metric("ToolLatency", elapsed_ms / 1000, unit="Seconds")

            _audit_put(audit_table, {
                "request_id": rid,
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "BLOCKED",
                "user_id": uid,
                "model": model,
                "reason": reason,
                "elapsed_ms": elapsed_ms,
            })

            logger.warning("generate_image_blocked request_id=%s reason=%s elapsed_ms=%s", rid, reason, elapsed_ms)

            return ImageGenerationResult(
                success=False,
                request_id=rid,
                status="BLOCKED",
                message=msg,
                reason=guard.get("reason"),
            ).model_dump()

        log_metric("GuardrailApprovals", 1)

        # 2) Generate image bytes
        log_step(logger, "IMAGE_GENERATION_START", rid, uid, f"Starting image generation with {model}", model=model)

        try:
            gen_started = time.time()
            image_bytes = await bedrock_client.generate_image(
                prompt=prompt,
                model=model,
                width=width,
                height=height,
                style=style,
                cfg_scale=cfg_scale,
                steps=steps,
            )
            gen_elapsed_s = time.time() - gen_started

            log_step(
                logger,
                "IMAGE_GENERATION_COMPLETE",
                rid,
                uid,
                f"Image generated successfully in {gen_elapsed_s:.2f}s",
                generation_time_s=gen_elapsed_s,
                image_size_bytes=len(image_bytes),
            )

            log_metric("ImageGenerationTime", gen_elapsed_s, unit="Seconds")
        except Exception as e:
            elapsed_ms = int((time.time() - started) * 1000)
            err = f"{type(e).__name__}: {str(e)}"

            log_step(
                logger,
                "IMAGE_GENERATION_ERROR",
                rid,
                uid,
                f"Image generation failed: {err}",
                level="ERROR",
                error=err,
                elapsed_ms=elapsed_ms,
            )

            log_metric("ImageGenerationFailures", 1)
            log_metric("ToolFailures", 1)
            log_metric("ToolLatency", elapsed_ms / 1000, unit="Seconds")

            _audit_put(audit_table, {
                "request_id": rid,
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED_GENERATION",
                "user_id": uid,
                "model": model,
                "error": err[:2000],
                "elapsed_ms": elapsed_ms,
            })

            logger.exception("generate_image_failed request_id=%s elapsed_ms=%s", rid, elapsed_ms)
            raise

        # 3) Upload to S3
        log_step(logger, "S3_UPLOAD_START", rid, uid, "Starting S3 upload")

        image_id: Optional[str] = None
        try:
            image_id = str(uuid.uuid4())
            s3_result = await s3_client.upload_image(
                image_data=image_bytes,
                image_id=image_id,
                metadata={"request_id": rid, "user_id": uid, "model": model},
            )

            log_step(
                logger,
                "S3_UPLOAD_COMPLETE",
                rid,
                uid,
                f"Image uploaded to S3: {s3_result['key']}",
                s3_key=s3_result["key"],
                s3_bucket=s3_result.get("bucket"),
                image_id=image_id,
                size_bytes=s3_result.get("size"),
            )

            log_metric("S3Uploads", 1)
        except Exception as e:
            elapsed_ms = int((time.time() - started) * 1000)
            err = f"{type(e).__name__}: {str(e)}"

            log_step(
                logger,
                "S3_UPLOAD_ERROR",
                rid,
                uid,
                f"S3 upload failed: {err}",
                level="ERROR",
                error=err,
                image_id=image_id,
                elapsed_ms=elapsed_ms,
            )

            log_metric("S3UploadFailures", 1)
            log_metric("ToolFailures", 1)
            log_metric("ToolLatency", elapsed_ms / 1000, unit="Seconds")

            _audit_put(audit_table, {
                "request_id": rid,
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED_S3_UPLOAD",
                "user_id": uid,
                "model": model,
                "image_id": image_id,
                "error": err[:2000],
                "elapsed_ms": elapsed_ms,
            })

            logger.exception("s3_upload_failed request_id=%s elapsed_ms=%s", rid, elapsed_ms)
            raise

        # 4) Presigned URL
        log_step(logger, "PRESIGN_URL_START", rid, uid, "Generating presigned URL")

        try:
            url = await s3_client.generate_presigned_url(s3_key=s3_result["key"])

            log_step(
                logger,
                "PRESIGN_URL_COMPLETE",
                rid,
                uid,
                "Presigned URL generated successfully",
                url_expiry_seconds=int(secrets["PRESIGNED_URL_EXPIRY"]),
            )
        except Exception as e:
            elapsed_ms = int((time.time() - started) * 1000)
            err = f"{type(e).__name__}: {str(e)}"

            log_step(
                logger,
                "PRESIGN_URL_ERROR",
                rid,
                uid,
                f"Presigned URL generation failed: {err}",
                level="ERROR",
                error=err,
                s3_key=s3_result.get("key") if isinstance(s3_result, dict) else None,
                elapsed_ms=elapsed_ms,
            )

            log_metric("PresignFailures", 1)
            log_metric("ToolFailures", 1)
            log_metric("ToolLatency", elapsed_ms / 1000, unit="Seconds")

            _audit_put(audit_table, {
                "request_id": rid,
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED_PRESIGN",
                "user_id": uid,
                "model": model,
                "image_id": image_id,
                "s3_key": s3_result.get("key"),
                "error": err[:2000],
                "elapsed_ms": elapsed_ms,
            })

            logger.exception("presign_failed request_id=%s elapsed_ms=%s", rid, elapsed_ms)
            raise

        elapsed_ms = int((time.time() - started) * 1000)

        # Metrics: success + latency
        log_metric("ImagesGenerated", 1)
        log_metric("ToolSuccess", 1)
        log_metric("ToolLatency", elapsed_ms / 1000, unit="Seconds")

        log_step(
            logger,
            "REQUEST_SUCCESS",
            rid,
            uid,
            f"Image generation completed successfully in {elapsed_ms}ms",
            image_id=image_id,
            s3_key=s3_result["key"],
            elapsed_ms=elapsed_ms,
            model=model,
            size=f"{width}x{height}",
        )

        # Audit: SUCCEEDED
        _audit_put(audit_table, {
            "request_id": rid,
            "ts": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCEEDED",
            "user_id": uid,
            "model": model,
            "image_id": image_id,
            "s3_key": s3_result["key"],
            "elapsed_ms": elapsed_ms,
            "metadata": metadata,
        })

        logger.info(
            "generate_image_success request_id=%s image_id=%s s3_key=%s elapsed_ms=%s",
            rid, image_id, s3_result["key"], elapsed_ms
        )

        return ImageGenerationResult(
            success=True,
            request_id=rid,
            image_url=url,
            image_id=image_id,
            model_used=model,
            s3_key=s3_result["key"],
            expires_in=int(secrets["PRESIGNED_URL_EXPIRY"]),
            elapsed_ms=elapsed_ms,
            status="SUCCEEDED",
        ).model_dump()