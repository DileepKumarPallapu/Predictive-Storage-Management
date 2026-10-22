import sys
import os

# Add backend directory to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_path)

from app.main import initialize_database_and_seed_demo

if __name__ == "__main__":
    print("=" * 60)
    print("AEGISSTOR - Standalone Database Seeder")
    print("=" * 60)
    initialize_database_and_seed_demo()
    print("Seed process completed successfully.")
