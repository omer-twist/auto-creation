import os
from dotenv import load_dotenv

load_dotenv()

# API Keys and Config - loaded from .env
PLACID_API_TOKEN = os.getenv("PLACID_API_TOKEN")
PLACID_TEMPLATE_UUID = os.getenv("PLACID_TEMPLATE_UUID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")

# Monday.com column IDs (board structure)
MONDAY_COL_DATE = "date_mkyh6m6f"
MONDAY_COL_STATUS = "color_mkyhm0pa"
MONDAY_COL_SITE = "dropdown_mkyhy55m"
MONDAY_COL_CREATIVES = "file_mky7b1ww"
MONDAY_COL_URL = "text_mky7650h"
MONDAY_COL_CONTENT_MANAGER = "color_mkyhe4e6"
MONDAY_GROUP_ID = "topics"

# Monday.com constant values
MONDAY_SITE_VALUE = {"ids": [1]}  # "bst"
