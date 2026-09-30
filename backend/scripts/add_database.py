import sqlite3
import os


def connect_database(database_path: str):
    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    return cursor


def create_table(database_name: str, table_name: str):

    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "../../", f"{database_name}.db")

    cursor = connect_database(db_path)
    query = """
    CREATE TABLE IF NOT EXISTS video_analysis (
        "Video ID" TEXT PRIMARY KEY,
        "Video URL" TEXT NOT NULL,
        "Video Metadata" TEXT,
        "Transcript" TEXT,
        "OCR Text" TEXT,
        "Compliance Result" TEXT,
        "Status" TEXT NOT NULL,
        "Report" TEXT
    );
    """
    try:
        cursor.execute(query)
    except Exception as e:
        raise Exception(f"Failed to Create Table: {str(e)}")


if __name__ == "__main__":
    create_table("brand_guardian", "video_analysis")
