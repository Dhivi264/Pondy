from app.db import SessionLocal
from app.models.user import User
from app.auth import get_password_hash

db = SessionLocal()
existing = db.query(User).filter(User.username == "admin").first()
if not existing:
    admin = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        role="admin",
        full_name="System Admin"
    )
    db.add(admin)
    db.commit()
    print("Admin created.")
else:
    print("Admin exists, updating password.")
    existing.password_hash = get_password_hash("admin123")
    db.commit()
db.close()
