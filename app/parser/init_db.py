import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.parser.database import DB

logging.info("Database tables created successfully")

if __name__ == "__main__":
    logging.info("Database initialization complete")
