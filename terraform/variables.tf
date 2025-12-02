variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "function_name" {
  description = "Lambda function name"
  type        = string
  default     = "campaigns-generator"
}

variable "placid_api_token" {
  description = "Placid API token"
  type        = string
  sensitive   = true
}

variable "placid_template_uuid" {
  description = "Placid template UUID"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "monday_api_key" {
  description = "Monday.com API key"
  type        = string
  sensitive   = true
}

variable "monday_board_id" {
  description = "Monday.com board ID"
  type        = string
}
