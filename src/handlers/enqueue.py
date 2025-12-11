"""AWS Lambda handler for HTTP to SQS enqueue."""

import base64
import json
import os

import boto3

sqs = boto3.client("sqs")
QUEUE_URL = os.environ["QUEUE_URL"]


def handler(event, context):
    """
    HTTP to SQS proxy.

    Receives HTTP request and queues the body to SQS for async processing.
    """
    body = event.get("body", "{}")

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    response = sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=body)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "queued", "messageId": response["MessageId"]}),
    }
