from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/analyzer", tags=["analyzer"])


class AnalyzerRunRequest(BaseModel):
    log_path: str


@router.post("/run")
def run_analyzer(body: AnalyzerRunRequest, request: Request) -> dict:
    try:
        return request.app.state.analyzer_service.run(body.log_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
