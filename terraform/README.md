# Terraform Lambda Deployment

## Prerequisites

- AWS CLI configured with credentials
- Terraform >= 1.0
- Python 3.11

## Deploy

1. **Build the dependencies layer:**

   ```powershell
   # Windows
   .\build_layer.ps1
   ```

   ```bash
   # Linux/Mac
   ./build_layer.sh
   ```

2. **Create terraform.tfvars:**

   ```powershell
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Initialize and apply:**

   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## Configuration

| Variable | Description |
|----------|-------------|
| `aws_region` | AWS region (default: us-east-1) |
| `function_name` | Lambda function name |
| `placid_api_token` | Placid API token |
| `placid_template_uuid` | Placid template UUID |
| `openai_api_key` | OpenAI API key |
| `monday_api_key` | Monday.com API key |
| `monday_board_id` | Monday.com board ID |

## Lambda Details

- **Runtime:** Python 3.11
- **Timeout:** 300 seconds (5 minutes)
- **Memory:** 256 MB
- **Concurrency:** 3 (reserved)

Receives topic + metadata → generates 9 creatives via 3-stage pipeline → uploads to Monday.com (3 campaigns/rows)

## Invoke

```bash
aws lambda invoke \
  --function-name campaigns-generator \
  --payload '{"body": "{\"topic\": \"Test\", \"event\": \"Black Friday\", \"discount\": \"up to 50%\", \"page_type\": \"category\"}"}' \
  response.json
```

Or use the Function URL output.
