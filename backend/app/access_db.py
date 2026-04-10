import os
import pyodbc
from app.config import settings


def get_connection_string() -> str:
    return (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        rf"DBQ={settings.accdb_path};"
    )


def get_db_connection():
    conn = pyodbc.connect(get_connection_string())
    try:
        yield conn
    finally:
        conn.close()


def initialize_db():
    """Create the necessary tables and directories for real-time tracking."""
    # Ensure directories exist
    os.makedirs("data/faces", exist_ok=True)
    os.makedirs("data/recordings", exist_ok=True)

    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    try:
        # Check if TrackingLogs exists
        try:
            cursor.execute("SELECT TOP 1 ID FROM TrackingLogs")
        except pyodbc.Error:
            # Table doesn't exist, create it
            print("[DB] Creating TrackingLogs table...")
            cursor.execute("""
                CREATE TABLE TrackingLogs (
                    ID AUTOINCREMENT PRIMARY KEY,
                    EmployeeID SHORTTEXT,
                    CameraID SHORTTEXT,
                    SpottedAt DATETIME,
                    Zone SHORTTEXT
                )
            """)
            conn.commit()
    except pyodbc.Error as e:
        print(f"[DB] Initialization error: {e}")
    finally:
        conn.close()
