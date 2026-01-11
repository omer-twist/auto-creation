"""AWS Lambda handler for HTTP to SQS enqueue + config API."""

import base64
import json
import os

import boto3

sqs = boto3.client("sqs")
QUEUE_URL = os.environ.get("QUEUE_URL", "")


def handler(event, context):
    """
    HTTP router for enqueue and config endpoints.

    GET /config - Returns creative type configurations
    POST /      - Queues request body to SQS
    """
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    path = event.get("rawPath", "/")

    # GET /config - serve creative type configs
    if method == "GET" and path == "/config":
        from src.serializers import serialize_all
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(serialize_all()),
        }

    # POST / - enqueue to SQS
    body = event.get("body", "{}")

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    response = sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=body)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "queued", "messageId": response["MessageId"]}),
    }
