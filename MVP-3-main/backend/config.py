"""
Configuration module for Servex Holdings backend.
Handles environment variables and application settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# Application Settings
APP_TITLE = "Servex Holdings Logistics API"
APP_VERSION = "2.0.0"

# CORS Settings (if needed in future)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
]
