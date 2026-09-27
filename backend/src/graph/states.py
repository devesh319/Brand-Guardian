from typing import TypedDict, Optional, Dict, Any, List, Annotated
import operator


class ComplianceIssue(TypedDict):
    """
    Defines the Schema for a Single Compliance Result
    """

    category: str
    description: str
    severity: str
    timestamp: Optional[str]


class VideoAuditState(TypedDict):
    """
    Defines the State for LangGraph Graph Execution
    """

    # Input Params
    video_url: str
    video_id: str

    # Data Ingestion and Extraction
    local_file_path: Optional[str]
    video_metadata: Dict[str, Any]
    transcript: Optional[str]
    ocr_text: List[str]

    # Analysis Output
    compliance_result: Annotated[List[ComplianceIssue], operator.add]

    # Final Deliverables
    final_status: str
    final_report: str

    # Observability
    errors: Annotated[List[str], operator.add]
