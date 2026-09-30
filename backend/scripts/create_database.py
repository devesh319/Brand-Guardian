import sqlite3
import os

# from backend.utils.db_utils import connect_database
from backend.utils.db_utils import connect_database


def create_table(database_name: str, table_name: str):

    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "../../", f"{database_name}.db")

    connection = connect_database(db_path)
    cursor = connection.cursor()
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
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise Exception(f"Failed to Create Table: {str(e)}")
    finally:
        connection.close()


if __name__ == "__main__":
    create_table("brand_guardian", "video_analysis")
