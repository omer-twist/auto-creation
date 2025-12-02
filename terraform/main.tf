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

  reserved_concurrent_executions = 3  # Concurrency limit

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

# Function URL (optional - for easy HTTP access)
resource "aws_lambda_function_url" "image_generator_url" {
  function_name      = aws_lambda_function.image_generator.function_name
  authorization_type = "NONE"  # Change to AWS_IAM for production
}
