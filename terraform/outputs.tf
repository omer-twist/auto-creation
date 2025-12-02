output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.image_generator.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.image_generator.arn
}

output "lambda_function_url" {
  description = "Lambda function URL"
  value       = aws_lambda_function_url.image_generator_url.function_url
}

output "reserved_concurrency" {
  description = "Reserved concurrent executions"
  value       = aws_lambda_function.image_generator.reserved_concurrent_executions
}
