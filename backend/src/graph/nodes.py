import json
import logging
import re
import os
from typing import Any, Dict

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_azure_ai.vectorstores import AzureSearch
from langchain.messages import HumanMessage, SystemMessage

from backend.src.graph.states import VideoAuditState
from backend.src.services.video_indexer import VideoIndexerService

# Configure the logger
logger = logging.getLogger("brand-guardian")
logging.basicConfig(level=logging.INFO)


# Node 1: Video Indexer
def video_indexer(state: VideoAuditState) -> Dict[str, Any]:
    """
    Downloads the youtube video from the URL,
    Uploads to the Azure Video Indexer,
    Extracts the Insights
    """

    video_url = state.get("video_url")
    video_id_input = state.get("video_id", "video_demo")

    logger.info(f"---- [Node:Indexer] Processing : {video_url}")

    local_file_name = "temp_audit_video.mp4"

    try:
        vi_service = VideoIndexerService()

        if "youtube.com" in video_url or "youtu.be" in video_url:
            local_path = vi_service.download_youtube_video(
                video_url, output_path=local_file_name
            )
        else:
            raise Exception("Please provide a valid Youtube URL")

        azure_video_id = vi_service.upload_video(local_path, video_name=video_id_input)

        logger.info(f"Upload Success. Azure ID: {azure_video_id}")

        if os.path.exists(local_path):
            os.remove(local_path)

        raw_insights = vi_service.wait_for_processing(azure_video_id)
        clean_data = vi_service.extract_data(raw_insights)

        logger.info("--- [Node:Indexer] Extraction Complete -------------")

        return clean_data
    except Exception as e:
        logger.error(f"Video Indexer Failed: {e}")

        return {
            "errors": [str(e)],
            "final_status": "FAIL",
            "transcript": "",
            "ocr_text": [],
        }


# Node 2: Compliance Auditor
def audit_content(state: VideoAuditState) -> Dict[str, Any]:
    """
    Performs Retrieval Augmented Generation to Audit the Content of Brand Video
    """

    logger.info("--- [Node: Auditor] Querying Knowledge Base & LLM")

    transcript = state.get("transcript", "")

    if not transcript:
        logger.warning("No Transcript Available. Skippimg Audit......")
        return {
            "final_status": "FAIL",
            "final_report": "Audit Skipped because Video transcription failed (No transcript)",
        }

    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-3-small",
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )

    vector_store = AzureSearch(
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_API_KEY"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        embedding_function=embeddings.embed_query,
    )

    # RAG Retrieval
    ocr_text = state.get("ocr_text", [])
    query_text = f"{transcript} {''.join(ocr_text)}"
    docs = vector_store.similarity_search(query_text, k=3)
    retrieved_rules = "\n\n".join([doc.content for doc in docs])

    system_prompt = f"""
    You are a Senior Brand Compliance Auditor.
    OFFICIAL REGULATORY RULES:
    {retrieved_rules}
    INSTRUCTIONS:
    1. Analyze the transcript and OCR text below.
    2. Identify any violation of the rules.
    3. Return strictly JSON in the following format.
    {{
        "compliance_results": [
            {{
                "category": "Claim Validation",
                "severity": "CRITICAL",
                "description": "Explaination of the violation..."
            }}
        ],
        "final_status": "FAIL",
        "final_report": "Summary of the findings..."
    }}

    If no violations are found, set "status" to pass and "compliance_results" to [].
    """

    user_message = f"""
    VIDEO_METADATA: {state.get("video_metadata", {})}
    TRANSCRIPT: {transcript}
    ON-SCREEN TEXT (OCR): {ocr_text}
    """

    try:
        response = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
        )
        content = response.content

        if "```" in content:
            content = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL).group(1)

        audit_data = json.loads(content.strip())

        return {
            "compliance_result": audit_data.get("compliance_results", []),
            "final_status": audit_data.get("final_status", "FAIL"),
            "final_report": audit_data.get("final_report", "No report generated!"),
        }
    except Exception as e:
        logger.error(f"System failed in Auditor Mode: {str(e)}")
        logger.error(
            f"RAW LLM Response: {response.content if response in locals() else None}"
        )

        return {"errors": [str(e)], "final_status": "FAIL"}
