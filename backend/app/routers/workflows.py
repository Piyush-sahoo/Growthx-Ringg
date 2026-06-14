"""Workflow template + deploy endpoints (S3/S4)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import llm
from ..deploy import deploy_workflow
from ..graph import WorkflowGraph, validate_graph
from ..ringg import RinggError, ringg_client
from ..store import store
from ..templates import get_template, list_templates

router = APIRouter(prefix="/workflows", tags=["workflows"])


class DeployRequest(BaseModel):
    template_id: str | None = None
    graph: WorkflowGraph | None = None


class GenerateRequest(BaseModel):
    prompt: str
    base_template_id: str | None = None


@router.get("/templates")
def templates() -> list[dict]:
    return list_templates()


@router.get("/templates/{template_id}", response_model=WorkflowGraph)
def template(template_id: str) -> WorkflowGraph:
    g = get_template(template_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return g


@router.get("/credits")
async def credits() -> dict:
    """Available Ringg credits (call before placing runs — credits fail silently)."""
    try:
        return {"credits": await ringg_client.credits()}
    except RinggError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/deploy")
async def deploy(req: DeployRequest) -> dict:
    """Create/attach Ringg assistants for a workflow's call nodes and persist it."""
    if req.graph is not None:
        graph = req.graph
    elif req.template_id is not None:
        graph = get_template(req.template_id)
        if graph is None:
            raise HTTPException(status_code=404, detail="Template not found")
        graph = graph.model_copy(deep=True)
    else:
        raise HTTPException(status_code=400, detail="Provide template_id or graph")

    try:
        validate_graph(graph)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid graph: {exc}") from exc

    summary = await deploy_workflow(graph)
    await store.save_workflow(graph.model_dump(mode="json"))
    return {"deployment": summary, "graph": graph.model_dump(mode="json")}


@router.post("/generate")
def generate(req: GenerateRequest) -> dict:
    """Generate a workflow graph from a natural-language prompt (Gemini, S9).

    Optionally seeds from a base template. Falls back to the base (or a minimal
    valid graph) when generation fails; raises 422 if nothing valid can be made.
    """
    base = None
    if req.base_template_id is not None:
        tpl = get_template(req.base_template_id)
        if tpl is None:
            raise HTTPException(status_code=404, detail="Base template not found")
        base = tpl.model_dump(mode="json")

    raw = llm.generate_workflow(req.prompt, base)

    def _validated(data: dict) -> WorkflowGraph | None:
        try:
            g = WorkflowGraph.model_validate(data)
            validate_graph(g)
            return g
        except ValueError:
            return None

    graph = _validated(raw)
    if graph is None and base is not None:
        graph = _validated(base)
    if graph is None:
        raise HTTPException(status_code=422, detail="Generated graph failed validation")

    return {"graph": graph.model_dump(mode="json")}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> dict:
    g = await store.get_workflow(workflow_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return g
