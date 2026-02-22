"""FastAPI server for the AI Finance Assistant."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.workflow.orchestrator import process_query
from src.utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="AI Finance Assistant",
    description=(
        "A modular AI-powered finance education assistant. "
        "Provides general financial education only — not personalised advice."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str

    model_config = {"json_schema_extra": {"example": {"question": "What is compound interest?"}}}


class AskResponse(BaseModel):
    question: str
    answer: str
    agent: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check")
def health_check() -> dict:
    """Returns 200 OK when the service is running."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse, summary="Ask a finance question")
def ask(request: AskRequest) -> AskResponse:
    """
    Route a finance question through the orchestrator and return the answer.

    Routing is keyword-based via `core/router`; the appropriate agent is
    selected automatically from the 6 available specialists:
      finance_qa_agent | portfolio_analysis_agent | market_analysis_agent |
      goal_planning_agent | news_synthesizer_agent | tax_education_agent

    Returns general financial education only — no personalised advice.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be empty.")

    logger.info("POST /ask  question=%s", question[:80])
    try:
        result = process_query(question)
        return AskResponse(
            question=question,
            answer=result["answer"],
            agent=result["agent"],
        )
    except Exception as exc:
        logger.error("Error processing question: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Entry point (local dev) ────────────────────────────────────────────────────

if __name__ == "__main__":
    import yaml
    from pathlib import Path
    import uvicorn

    _cfg_path = Path(__file__).resolve().parents[2] / "config.yaml"
    _server_cfg: dict = {}
    if _cfg_path.exists():
        with open(_cfg_path) as f:
            _server_cfg = yaml.safe_load(f).get("server", {})

    uvicorn.run(
        "src.web_app.server:app",
        host=_server_cfg.get("host", "0.0.0.0"),
        port=int(_server_cfg.get("port", 8000)),
        reload=True,
    )
