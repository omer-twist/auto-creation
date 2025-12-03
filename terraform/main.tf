terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# SQS permissions for Lambda
resource "aws_iam_role_policy_attachment" "lambda_sqs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

# SQS Queue for queuing requests
resource "aws_sqs_queue" "campaigns_queue" {
  name                       = "${var.function_name}-queue"
  visibility_timeout_seconds = 360  # 6 min (longer than Lambda timeout)
  message_retention_seconds  = 86400  # 1 day
  receive_wait_time_seconds  = 20  # Long polling
}

# Policy to allow sending messages to SQS
resource "aws_sqs_queue_policy" "campaigns_queue_policy" {
  queue_url = aws_sqs_queue.campaigns_queue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.campaigns_queue.arn
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "image_generator" {
  function_name = var.function_name
  role          = aws_iam_role.lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300  # 5 minutes (each run takes ~2 min)
  memory_size   = 256

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  layers = [aws_lambda_layer_version.dependencies.arn]

  # No reserved concurrency - SQS trigger handles it

  environment {
    variables = {
      PLACID_API_TOKEN     = var.placid_api_token
      PLACID_TEMPLATE_UUID = var.placid_template_uuid
      OPENAI_API_KEY       = var.openai_api_key
      MONDAY_API_KEY       = var.monday_api_key
      MONDAY_BOARD_ID      = var.monday_board_id
    }
  }
}

# Package Lambda code
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda.zip"

  source {
    content  = file("${path.module}/../handler.py")
    filename = "handler.py"
  }

  source {
    content  = file("${path.module}/../config.py")
    filename = "config.py"
  }

  source {
    content  = file("${path.module}/../monday_client.py")
    filename = "monday_client.py"
  }

  # Pipeline module
  source {
    content  = file("${path.module}/../pipeline/__init__.py")
    filename = "pipeline/__init__.py"
  }

  source {
    content  = file("${path.module}/../pipeline/models.py")
    filename = "pipeline/models.py"
  }

  source {
    content  = file("${path.module}/../pipeline/pipeline.py")
    filename = "pipeline/pipeline.py"
  }

  source {
    content  = file("${path.module}/../pipeline/prompt_loader.py")
    filename = "pipeline/prompt_loader.py"
  }

  source {
    content  = file("${path.module}/../pipeline/stages.py")
    filename = "pipeline/stages.py"
  }

  source {
    content  = file("${path.module}/../pipeline/tsv_parser.py")
    filename = "pipeline/tsv_parser.py"
  }

  # Placid module
  source {
    content  = file("${path.module}/../placid/__init__.py")
    filename = "placid/__init__.py"
  }

  source {
    content  = file("${path.module}/../placid/client.py")
    filename = "placid/client.py"
  }

  source {
    content  = file("${path.module}/../placid/config.py")
    filename = "placid/config.py"
  }

  # Config prompts
  source {
    content  = file("${path.module}/../config/prompts/creator.txt")
    filename = "config/prompts/creator.txt"
  }

  source {
    content  = file("${path.module}/../config/prompts/editor.txt")
    filename = "config/prompts/editor.txt"
  }

  source {
    content  = file("${path.module}/../config/prompts/final_toucher.txt")
    filename = "config/prompts/final_toucher.txt"
  }
}

# Lambda Layer for dependencies
resource "aws_lambda_layer_version" "dependencies" {
  layer_name          = "${var.function_name}-dependencies"
  filename            = "${path.module}/layer.zip"
  compatible_runtimes = ["python3.11"]
  source_code_hash    = filebase64sha256("${path.module}/layer.zip")

  lifecycle {
    create_before_destroy = true
  }
}

# SQS Event Source Mapping - triggers worker Lambda from queue with max 3 concurrent
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn                   = aws_sqs_queue.campaigns_queue.arn
  function_name                      = aws_lambda_function.image_generator.arn
  batch_size                         = 1
  maximum_batching_window_in_seconds = 0
  scaling_config {
    maximum_concurrency = 3  # MAX 3 CONCURRENT - this is the real queue limit
  }
}

# Enqueue Lambda - receives HTTP, puts in SQS, returns immediately
resource "aws_lambda_function" "enqueue" {
  function_name = "${var.function_name}-enqueue"
  role          = aws_iam_role.lambda_role.arn
  handler       = "enqueue.lambda_handler"
  runtime       = "python3.11"
  timeout       = 10
  memory_size   = 128

  filename         = data.archive_file.enqueue_zip.output_path
  source_code_hash = data.archive_file.enqueue_zip.output_base64sha256

  environment {
    variables = {
      QUEUE_URL = aws_sqs_queue.campaigns_queue.url
    }
  }
}

data "archive_file" "enqueue_zip" {
  type        = "zip"
  output_path = "${path.module}/enqueue.zip"

  source {
    content  = <<-EOF
import json
import os
import boto3

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['QUEUE_URL']

def lambda_handler(event, context):
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
    filename = "enqueue.py"
  }
}

# IAM policy for enqueue Lambda to send to SQS
resource "aws_iam_role_policy" "enqueue_sqs_send" {
  name = "${var.function_name}-enqueue-sqs-send"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "sqs:SendMessage"
      Resource = aws_sqs_queue.campaigns_queue.arn
    }]
  })
}

# Function URL for enqueue Lambda (this is the HTTP endpoint users will call)
resource "aws_lambda_function_url" "enqueue_url" {
  function_name      = aws_lambda_function.enqueue.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type"]
  }
}
