import os
from dotenv import load_dotenv

load_dotenv()

# API Keys and Config - loaded from .env
PLACID_API_TOKEN = os.getenv("PLACID_API_TOKEN")
PLACID_TEMPLATE_UUID = os.getenv("PLACID_TEMPLATE_UUID")
PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID = os.getenv("PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID")
PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID_WHITE = os.getenv("PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID_WHITE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REMOVEBG_API_KEY = os.getenv("REMOVEBG_API_KEY")

# Monday.com column IDs (board structure) - Auto Creation (eComm) board
MONDAY_COL_DATE = "date4"
MONDAY_COL_STATUS = "status"
MONDAY_COL_SITE = "dropdown7"
MONDAY_COL_CREATIVES = "files1"
MONDAY_COL_URL = "url"
MONDAY_COL_CONTENT_MANAGER = "status_19"
MONDAY_GROUP_ID = "topics"

# Monday.com constant values
MONDAY_SITE_VALUE = {"ids": [1]}  # "bst"
MONDAY_CONTENT_MANAGER_VALUE = {"index": 7}  # "om"
