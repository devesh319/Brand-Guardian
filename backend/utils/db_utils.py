import json
import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATABASE_PATH = Path(__file__).resolve().parents[2] / "brand_guardian.db"

VIDEO_ANALYSIS_COLUMNS = (
    '"Video ID"',
    '"Video URL"',
    '"Video Metadata"',
    '"Transcript"',
    '"OCR Text"',
    '"Compliance Result"',
    '"Status"',
    '"Report"',
)


def connect_database(database_path: str | Path = DATABASE_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with foreign-key enforcement enabled."""
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_video_analysis(
    url: str, database_path: str | Path = DATABASE_PATH
) -> dict[str, Any] | str:
    """Return the persisted analysis for a video URL, or an empty string."""
    if not url or not url.strip():
        raise ValueError("Video URL is required")

    query = """
        SELECT "Video ID", "Status", "Compliance Result", "Report"
        FROM video_analysis
        WHERE "Video URL" = ?
    """

    try:
        with closing(connect_database(database_path)) as connection:
            with connection:
                row = connection.execute(query, (url,)).fetchone()
    except sqlite3.Error:
        logger.exception("Failed to retrieve video analysis for URL %r", url)
        raise

    if row is None:
        return ""

    return {
        "video_id": row[0],
        "status": row[1],
        "compliance_result": row[2],
        "final_report": row[3],
    }


def add_video_analysis(
    analysis: dict[str, Any], database_path: str | Path = DATABASE_PATH
) -> bool:
    """Insert or update an analysis and verify it can be read back."""
    if not isinstance(analysis, dict):
        raise TypeError("analysis must be a dictionary")

    video_id = analysis.get("video_id")
    video_url = analysis.get("video_url")
    if not video_id:
        raise ValueError("Video ID is required")
    if not video_url:
        raise ValueError("Video URL is required")

    query = f"""
        INSERT INTO video_analysis ({", ".join(VIDEO_ANALYSIS_COLUMNS)})
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT("Video ID") DO UPDATE SET
            "Video URL" = excluded."Video URL",
            "Video Metadata" = excluded."Video Metadata",
            "Transcript" = excluded."Transcript",
            "OCR Text" = excluded."OCR Text",
            "Compliance Result" = excluded."Compliance Result",
            "Status" = excluded."Status",
            "Report" = excluded."Report"
    """

    values = (
        video_id,
        video_url,
        json.dumps(analysis.get("video_metadata", "")),
        analysis.get("transcript", ""),
        json.dumps(analysis.get("ocr_text", "")),
        json.dumps(analysis.get("compliance_result", "")),
        analysis.get("final_status", ""),
        analysis.get("final_report", ""),
    )

    try:
        with closing(connect_database(database_path)) as connection:
            with connection:
                connection.execute(query, values)
                persisted_id = connection.execute(
                    'SELECT "Video ID" FROM video_analysis WHERE "Video ID" = ?',
                    (video_id,),
                ).fetchone()
                if persisted_id is None:
                    raise RuntimeError(
                        f"Video analysis was not persisted for video ID {video_id!r}"
                    )
    except sqlite3.Error:
        logger.exception("Failed to persist video analysis for ID %r", video_id)
        raise

    return True
