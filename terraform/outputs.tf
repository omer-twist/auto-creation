output "lambda_function_name" {
  description = "Worker Lambda function name"
  value       = aws_lambda_function.image_generator.function_name
}

output "lambda_function_arn" {
  description = "Worker Lambda function ARN"
  value       = aws_lambda_function.image_generator.arn
}

output "enqueue_url" {
  description = "HTTP endpoint to queue jobs (call this from UI)"
  value       = aws_lambda_function_url.enqueue_url.function_url
}

output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.campaigns_queue.url
}

output "max_concurrency" {
  description = "Max concurrent Lambda executions (from SQS trigger)"
  value       = 3
}
