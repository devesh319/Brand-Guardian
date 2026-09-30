def print_results(final_state):

    print("----------- Workflow Execution Complete -----------")

    print("\n Compliance Audit Report.....")

    print(f"Video ID: {final_state.get("video_id")}")
    print(f"Status: {final_state.get("final_status")}")

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
