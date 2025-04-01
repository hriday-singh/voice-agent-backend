import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from app.database.db import DATABASE_URL, Base, engine
from app.models.models import OTP, OTPUsage, Admin, AgentTraffic
from app.utils.auth import get_password_hash

def rebuild_database():
    """Rebuild the database from scratch"""
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    
    print("Creating default admin account...")
    from sqlalchemy.orm import Session
    with Session(engine) as session:
        # Create default admin
        admin = Admin(
            username="cawadmin",
            password_hash=get_password_hash("adminc@w")
        )
        session.add(admin)
        session.commit()
    
    print("Database rebuilt successfully!")
    print("Default admin credentials:")
    print("Username: cawadmin")
    print("Password: adminc@w")

if __name__ == "__main__":
    # Confirm with user
    response = input("This will delete all data in the database. Are you sure? (y/N): ")
    if response.lower() == 'y':
        rebuild_database()
    else:
        print("Operation cancelled.") 