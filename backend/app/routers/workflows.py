"""Workflow template endpoints — the select-and-modify library (feeds S7/S8)."""

from fastapi import APIRouter, HTTPException

from ..graph import WorkflowGraph
from ..templates import get_template, list_templates

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/templates")
def templates() -> list[dict]:
    return list_templates()


@router.get("/templates/{template_id}", response_model=WorkflowGraph)
def template(template_id: str) -> WorkflowGraph:
    g = get_template(template_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return g
