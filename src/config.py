import os
from dotenv import load_dotenv

load_dotenv()

# API Keys and Config - loaded from .env
PLACID_API_TOKEN = os.getenv("PLACID_API_TOKEN")
PLACID_TEMPLATE_UUID = os.getenv("PLACID_TEMPLATE_UUID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")
