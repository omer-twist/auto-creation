import os
import requests
import time

from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("PLACID_API_TOKEN")
TEMPLATE_UUID = os.getenv("PLACID_TEMPLATE_UUID")

def main():
    url = f"https://api.placid.app/api/rest/{TEMPLATE_UUID}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "create_now": True,
        "layers": {
            "bg": {
                "background_color": "#3B027A"
            },
            "text": {
                "text": "test"
            }
        }
    }

    r = requests.post(url, json=payload, headers=headers)
    print("Create status:", r.status_code, r.text)
    r.raise_for_status()
    data = r.json()
    image_id = data["id"]
    print("Image ID:", image_id)

    poll_url = f"https://api.placid.app/api/rest/images/{image_id}"

    while True:
        time.sleep(2)
        p = requests.get(poll_url, headers=headers)
        print("Poll:", p.status_code, p.text)
        p.raise_for_status()
        img = p.json()
        if img["status"] in ("finished", "error"):
            print("Final:", img)
            break

if __name__ == "__main__":
    main()
