"""Monday.com API client."""

import json

import requests


class MondayClient:
    """Low-level Monday.com API client."""

    API_URL = "https://api.monday.com/v2"
    FILE_URL = "https://api.monday.com/v2/file"

    def __init__(self, api_key: str, board_id: str):
        self.api_key = api_key
        self.board_id = board_id

    def _get_headers(self) -> dict:
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    def create_item(
        self, item_name: str, column_values: dict, group_id: str = "topics"
    ) -> int:
        """Create a new item in Monday board. Returns item_id."""
        query = """
        mutation ($boardId: ID!, $groupId: String!, $itemName: String!, $columnValues: JSON!) {
            create_item (board_id: $boardId, group_id: $groupId, item_name: $itemName, column_values: $columnValues) {
                id
            }
        }
        """
        variables = {
            "boardId": self.board_id,
            "groupId": group_id,
            "itemName": item_name,
            "columnValues": json.dumps(column_values),
        }

        response = requests.post(
            self.API_URL,
            json={"query": query, "variables": variables},
            headers=self._get_headers(),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise Exception(f"Monday API error: {data['errors']}")

        return int(data["data"]["create_item"]["id"])

    def upload_file(
        self, item_id: int, column_id: str, file_bytes: bytes, filename: str
    ) -> dict:
        """Upload a file to a Monday.com file column."""
        query = f'mutation add_file($file: File!) {{ add_file_to_column (item_id: {item_id}, column_id: "{column_id}", file: $file) {{ id }} }}'

        files = {
            "query": (None, query),
            "variables[file]": (filename, file_bytes, "image/jpeg"),
        }
        headers = {"Authorization": self.api_key}

        response = requests.post(self.FILE_URL, files=files, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise Exception(f"Monday API error: {data['errors']}")

        return data
