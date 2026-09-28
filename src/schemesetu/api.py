from pathlib import Path
import os

from fastapi import FastAPI

from .models import AnalysisRequest, AnalysisResponse
from .repository import SchemeRepository
from .service import SchemeSetuService


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_schemes.json"
service = SchemeSetuService(SchemeRepository.from_json(os.environ.get("SCHEMESETU_CATALOG", DATA_PATH)))

app = FastAPI(title="SchemeSetu API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest) -> AnalysisResponse:
    return service.analyze(request)
