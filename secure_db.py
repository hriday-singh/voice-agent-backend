import os
import stat
from pathlib import Path
import sys
import shutil

def secure_database():
    """Secure the database file and directory"""
    data_dir = Path("data")
    db_file = data_dir / "app.db"
    
    print("Securing database...")
    
    # Create data directory if it doesn't exist
    data_dir.mkdir(exist_ok=True)
    
    # Set restrictive permissions on data directory
    if os.name != 'nt':  # Skip on Windows
        print("Setting directory permissions (owner only)...")
        os.chmod(data_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    
    # If database exists in root directory, move it to data directory
    old_db = Path("app.db")
    if old_db.exists():
        print("Moving database to secure location...")
        if db_file.exists():
            backup = data_dir / "app.db.backup"
            print(f"Creating backup at {backup}...")
            shutil.copy2(db_file, backup)
        shutil.move(old_db, db_file)
    
    # Set restrictive permissions on database file
    if os.name != 'nt':  # Skip on Windows
        if db_file.exists():
            print("Setting database file permissions (owner only)...")
            os.chmod(db_file, stat.S_IRUSR | stat.S_IWUSR)
    
    # Create .gitignore if it doesn't exist
    gitignore = Path(".gitignore")
    if not gitignore.exists():
        print("Creating .gitignore...")
        with open(gitignore, "a") as f:
            f.write("\n# Database\n")
            f.write("data/\n")
            f.write("*.db\n")
            f.write("*.db-journal\n")
            f.write("*.db-wal\n")
            f.write("*.db-shm\n")
    
    print("\nDatabase security enhancements:")
    print("1. Database moved to secure 'data' directory")
    print("2. Directory permissions set to owner-only access (Unix/Linux)")
    print("3. Database file permissions set to owner-only access (Unix/Linux)")
    print("4. Database files added to .gitignore")
    print("\nNote: On Windows, file permissions are handled by NTFS security.")

if __name__ == "__main__":
    secure_database() 