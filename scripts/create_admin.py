import sys
import os

# Add the parent directory to sys.path to allow importing from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from core.db.engine import engine
from core.db.models import User
from core.auth.security import get_password_hash
import getpass

def create_admin():
    if len(sys.argv) == 3:
        email = sys.argv[1]
        password = sys.argv[2]
    else:
        print("Create Admin User")
        email = input("Email: ")
        password = getpass.getpass("Password: ")
    
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if user:
            print(f"User {email} already exists. Updating password.")
            user.password_hash = get_password_hash(password)
            session.add(user)
            session.commit()
            print(f"Password updated for {email}.")
            return

        hashed_password = get_password_hash(password)
        admin_user = User(email=email, password_hash=hashed_password, role="admin", is_admin=True)
        session.add(admin_user)
        session.commit()
        print(f"Admin user {email} created successfully.")

if __name__ == "__main__":
    create_admin()
