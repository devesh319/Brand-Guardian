import uuid
import logging
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from datetime import datetime
from pydantic import BaseModel
from typing import List

from dotenv import load_dotenv

from backend.src.api.telemetry import set_telemetry
from backend.src.graph.workflow import app as compliance_graph
from backend.utils.db_utils import get_video_analysis, add_video_analysis

load_dotenv(override=True)

DB_PATH = (
    "/home/devesh/Desktop/Learnings/Projects/CompilanceQAPipeline/brand_guardian.db"
)

set_telemetry()

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
log_file = log_dir / f"app_{run_stamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)

logger = logging.getLogger("brand-guardian-api")

app = FastAPI(
    title="Brand Guardian",
    description="API for auditing video content against Youtube Compliance Rules",
    version="1.0.0",
)


class AuditRequest(BaseModel):
    video_url: str


class ComplianceIssue(BaseModel):
    category: str
    severity: str
    description: str


class AuditResponse(BaseModel):
    session_id: str
    video_id: str
    status: str
    final_report: str
    compliance_results: List[ComplianceIssue]


@app.post("/audit", response_model=AuditResponse)
async def audit_video(request: AuditRequest):
    session_id = uuid.uuid4().hex
    video_id = f"vid_{session_id}"

    logger.info(
        f"Recieved the Audit Request: {request.video_url} (Session: {session_id})"
    )

    initial_inputs = {
        "video_url": request.video_url,
        "video_id": video_id,
        "compliance_result": [],
        "errors": [],
    }

    try:
        logger.info(f"Querying DB for Video: {request.video_url}")
        results = get_video_analysis(request.video_url, DB_PATH)

        if results:
            logger.info(f"Found Results in Database.")
            return AuditResponse(
                session_id=session_id,
                video_id=video_id,
                status=results.get("status", "FAIL"),
                final_report=results.get("final_report", ""),
                compliance_results=results.get("compliance_result", "[]"),
            )

        logger.info(f"Results not in Database. Invoking Graph.")
        final_state = await compliance_graph.ainvoke(initial_inputs)

        add_video_analysis(final_state, DB_PATH)

        return AuditResponse(
            session_id=session_id,
            video_id=video_id,
            status=final_state.get("final_status", "FAIL"),
            final_report=final_state.get("final_report", ""),
            compliance_results=final_state.get("compliance_result", "[]"),
        )
    except Exception as e:
        logger.error(f"Audit Failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Workflow Execution Failed: {str(e)}"
        )


@app.get("/health")
def check_health():
    return {"status": "healthy", "service": "brand-guardian-ai"}
