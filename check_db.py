import sqlite3

def check_db():
    try:
        conn = sqlite3.connect('backend/production.db')
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        
        # Get cameras
        cursor.execute("SELECT * FROM cameras")
        cameras = cursor.fetchall()
        print(f"Cameras: {cameras}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
