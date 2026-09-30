from dotenv import load_dotenv
import json
import logging
import uuid

from backend.src.graph.workflow import app

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("brand-guardian-runner")


def run_cli_simulation():
    # Get Session ID
    session_id = uuid.uuid4()
    logger.info(f"Starting Audit Session: {session_id}")

    initial_inputs = {
        "video_url": "",
        "video_id": "",
        "compliance_rseults": [],
        "errors": [],
    }

    print("\n----------- Initializing Workflow -----------")
    print(f"Input Payload: \n {json.dumps(initial_inputs, indent=2)}")

    try:
        final_state = app.invoke(initial_inputs)

        print("----------- Workflow Execution Complete -----------")

        print("\n Compliance Audit Report.....")
        print(f"Video ID: {final_state.get("video_id")}")
        print(f"Status: {final_state.get("status")}")

        print("\n [ VIOLATIONS DETECTED ]")

        results = final_state.get("compliance_result", [])

        if results:
            for issue in results:
                print(
                    f" - [{issue.get("severity")}] [{issue.get("category")}] : {issue.get("description")}"
                )
        else:
            print("--------- No Violations Detected! ------------")

        print("\n--------- Final Summary-------------")
        print(final_state.get("final_report"))

    except Exception as e:
        logger.error(f"Failed to execute workflow: {str(e)}")
        raise Exception(f"Failure: {str(e)}")


if __name__ == "__main__":
    run_cli_simulation()
