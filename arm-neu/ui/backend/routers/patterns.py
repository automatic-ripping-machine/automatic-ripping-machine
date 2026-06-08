"""Pattern-token vocabulary endpoint - feeds the UI's pattern-editor
autocomplete. Sourced from arm_contracts.PATTERN_TOKENS so adding a new
token in contracts auto-flows through to the UI on the next BFF restart.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from arm_contracts import PATTERN_TOKENS

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


class PatternTokenInfo(BaseModel):
    field_name: str
    description: str


@router.get("/tokens", response_model=dict[str, PatternTokenInfo])
async def get_pattern_tokens():
    """Return all available naming-pattern tokens with their descriptions."""
    return {
        alias: PatternTokenInfo(field_name=field, description=desc)
        for alias, (field, desc, _accessor) in PATTERN_TOKENS.items()
    }
