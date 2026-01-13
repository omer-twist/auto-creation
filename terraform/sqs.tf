# SQS Queue for campaign jobs
resource "aws_sqs_queue" "campaigns" {
  name                       = "${var.function_name}-queue"
  visibility_timeout_seconds = 660 # 11 min (longer than Lambda 10 min timeout)
  message_retention_seconds  = 86400 # 1 day
  receive_wait_time_seconds  = 20 # Long polling
}

resource "aws_sqs_queue_policy" "campaigns" {
  queue_url = aws_sqs_queue.campaigns.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.campaigns.arn
      }
    ]
  })
}
