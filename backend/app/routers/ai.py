"""AI Explanation API routes for CodeCompass."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import FEATHERLESS_API_KEY, FEATHERLESS_MODEL
from app.services.ai_service import (
    get_symbol_for_explanation,
    explain_code_symbol,
    AIServiceConfigurationError,
    AITimeoutError,
    AIProviderError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


class ExplainCodeRequest(BaseModel):
    """Request payload for generating an AI explanation of a selected symbol."""
    symbol_id: int = Field(..., description="Authoritative symbol ID from active repository")
    query_context: Optional[str] = Field(
        None,
        max_length=250,
        description="Optional user search query context",
    )


@router.post("/explain")
def explain_symbol(req: ExplainCodeRequest):
    """Generate a grounded, defensive AI onboarding explanation for a selected symbol.

    Authoritative code snippet and metadata are retrieved directly from SQLite;
    client cannot supply arbitrary code or file paths.
    """
    # 1. Authoritative SQLite database lookup
    try:
        symbol_info = get_symbol_for_explanation(req.symbol_id)
    except Exception as exc:
        logger.error("Failed to lookup symbol %s: %s", req.symbol_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error retrieving symbol metadata.",
        )

    if not symbol_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol ID {req.symbol_id} was not found in the active repository.",
        )

    # 2. Invoke Featherless AI service with prompt injection defense
    try:
        return explain_code_symbol(
            symbol_info=symbol_info,
            query_context=req.query_context,
        )
    except AIServiceConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except AITimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error during AI explanation generation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the code explanation.",
        )


@router.get("/status")
def get_ai_status():
    """Retrieve AI provider configuration status without exposing API keys."""
    return {
        "configured": bool(FEATHERLESS_API_KEY and FEATHERLESS_API_KEY.strip()),
        "model": FEATHERLESS_MODEL,
        "provider": "Featherless AI",
    }
