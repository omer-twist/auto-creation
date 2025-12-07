# Worker Lambda
output "worker_function_name" {
  description = "Worker Lambda function name"
  value       = aws_lambda_function.worker.function_name
}

output "worker_function_arn" {
  description = "Worker Lambda function ARN"
  value       = aws_lambda_function.worker.arn
}

# Enqueue Lambda
output "enqueue_url" {
  description = "HTTP endpoint to queue jobs (call this from UI)"
  value       = aws_lambda_function_url.enqueue.function_url
}

# SQS
output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.campaigns.url
}

# ECR
output "ecr_repository_url" {
  description = "ECR repository URL for worker image"
  value       = aws_ecr_repository.worker.repository_url
}

# Deployment helper
output "docker_push_commands" {
  description = "Commands to build and push Docker image"
  value       = <<-EOF
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.worker.repository_url}
    docker build -t ${aws_ecr_repository.worker.repository_url}:latest .
    docker push ${aws_ecr_repository.worker.repository_url}:latest
    aws lambda update-function-code --function-name ${aws_lambda_function.worker.function_name} --image-uri ${aws_ecr_repository.worker.repository_url}:latest
  EOF
}
