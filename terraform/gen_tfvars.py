"""Generate terraform.tfvars from .env file"""
import sys
sys.path.insert(0, "..")

from config import (
    PLACID_API_TOKEN,
    PLACID_TEMPLATE_UUID,
    OPENAI_API_KEY,
    MONDAY_API_KEY,
    MONDAY_BOARD_ID,
)

tfvars = f'''aws_region           = "us-east-1"
function_name        = "campaigns-generator"
placid_api_token     = "{PLACID_API_TOKEN}"
placid_template_uuid = "{PLACID_TEMPLATE_UUID}"
openai_api_key       = "{OPENAI_API_KEY}"
monday_api_key       = "{MONDAY_API_KEY}"
monday_board_id      = "{MONDAY_BOARD_ID}"
'''

with open("terraform.tfvars", "w") as f:
    f.write(tfvars)

print("Generated terraform.tfvars from config")
