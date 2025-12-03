from openai import OpenAI

from placid.config import OPENAI_API_KEY


def generate_text(item: str) -> str:
    """Generate marketing text for an item using OpenAI."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[
            {
                "role": "system",
                "content": "Generate short, punchy marketing text (max 10 words) for social media images.",
            },
            {"role": "user", "content": f"Create text for: {item}"},
        ],
        max_completion_tokens=50,
    )

    return response.choices[0].message.content.strip()
