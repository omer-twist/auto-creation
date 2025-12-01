import json

import requests

MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_FILE_URL = "https://api.monday.com/v2/file"


def create_item(
    api_key: str, board_id: str, item_name: str, column_values: dict
) -> int:
    """Create a new item in Monday board. Returns item_id."""
    query = """
    mutation ($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
        create_item (board_id: $boardId, item_name: $itemName, column_values: $columnValues) {
            id
        }
    }
    """
    variables = {
        "boardId": board_id,
        "itemName": item_name,
        "columnValues": json.dumps(column_values),
    }

    response = requests.post(
        MONDAY_API_URL,
        json={"query": query, "variables": variables},
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise Exception(f"Monday API error: {data['errors']}")

    return int(data["data"]["create_item"]["id"])


def upload_file_to_column(
    api_key: str, item_id: int, column_id: str, file_bytes: bytes, filename: str
) -> dict:
    """Upload a file to a Monday.com file column."""
    query = f'mutation {{ add_file_to_column (item_id: {item_id}, column_id: "{column_id}") {{ id }} }}'

    files = {
        "query": (None, query),
        "variables[file]": (filename, file_bytes, "image/jpeg"),
    }
    headers = {"Authorization": api_key}

    response = requests.post(MONDAY_FILE_URL, files=files, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise Exception(f"Monday API error: {data['errors']}")

    return data
