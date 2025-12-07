# =============================================================================
# Worker Lambda (image-based) - processes campaign jobs from SQS
# =============================================================================

resource "aws_lambda_function" "worker" {
  function_name = "${var.function_name}-worker"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.worker.repository_url}:latest"
  timeout       = 300 # 5 minutes
  memory_size   = 256

  environment {
    variables = {
      PLACID_API_TOKEN     = var.placid_api_token
      PLACID_TEMPLATE_UUID = var.placid_template_uuid
      OPENAI_API_KEY       = var.openai_api_key
      MONDAY_API_KEY       = var.monday_api_key
      MONDAY_BOARD_ID      = var.monday_board_id
    }
  }

  depends_on = [aws_ecr_repository.worker]
}

# SQS trigger for worker
resource "aws_lambda_event_source_mapping" "worker_sqs" {
  event_source_arn                   = aws_sqs_queue.campaigns.arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 1
  maximum_batching_window_in_seconds = 0

  scaling_config {
    maximum_concurrency = 2 # Max concurrent executions
  }
}

# =============================================================================
# Enqueue Lambda (inline) - receives HTTP, queues to SQS
# =============================================================================

resource "aws_lambda_function" "enqueue" {
  function_name = "${var.function_name}-enqueue"
  role          = aws_iam_role.lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 10
  memory_size   = 128

  filename         = data.archive_file.enqueue.output_path
  source_code_hash = data.archive_file.enqueue.output_base64sha256

  environment {
    variables = {
      QUEUE_URL = aws_sqs_queue.campaigns.url
    }
  }
}

data "archive_file" "enqueue" {
  type        = "zip"
  output_path = "${path.module}/enqueue.zip"

  source {
    content  = <<-EOF
import json
import os
import boto3

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['QUEUE_URL']

def handler(event, context):
    body = event.get('body', '{}')
    if event.get('isBase64Encoded'):
        import base64
        body = base64.b64decode(body).decode('utf-8')

    response = sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=body)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'status': 'queued', 'messageId': response['MessageId']})
    }
EOF
    filename = "index.py"
  }
}

# Function URL for enqueue (HTTP endpoint)
resource "aws_lambda_function_url" "enqueue" {
  function_name      = aws_lambda_function.enqueue.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type"]
  }
}
