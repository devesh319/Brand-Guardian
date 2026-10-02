from dotenv import load_dotenv
import argparse
import json
import logging
import uuid

from backend.src.graph.workflow import app
from backend.utils.db_utils import get_video_analysis, add_video_analysis, DATABASE_PATH
from backend.utils.utils import print_results

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("brand-guardian-runner")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Run the compliance QA workflow.")
    parser.add_argument(
        "--url", "-u", required=True, help="URL of the video to analyze."
    )
    return parser.parse_args()


def run_cli_simulation(video_url):
    # Get Session ID
    session_id = uuid.uuid4().hex
    logger.info(f"Starting Audit Session: {session_id}")

    initial_inputs = {
        "video_url": video_url,
        "video_id": f"vid_{session_id[:8]}",
        "compliance_results": [],
        "errors": [],
    }

    print("\n----------- Initializing Workflow -----------")
    print(f"Input Payload: \n {json.dumps(initial_inputs, indent=2)}")

    try:
        logger.info(f"Querying DB for Video: {video_url}")
        results = get_video_analysis(video_url, DATABASE_PATH)

        if results:
            logger.info(f"Found Results in Database.")
            print_results(results)
            return

        logger.info(f"Results not in Database. Invoking Graph.")
        final_state = app.invoke(initial_inputs)

        print_results(final_state)

        add_video_analysis(final_state, DATABASE_PATH)

    except Exception as e:
        logger.error(f"Failed to execute workflow: {str(e)}")
        raise Exception(f"Failure: {str(e)}")


if __name__ == "__main__":
    args = parse_arguments()
    run_cli_simulation(args.url)
