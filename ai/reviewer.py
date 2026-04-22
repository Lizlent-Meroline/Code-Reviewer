from openai import OpenAI
from openai import RateLimitError

client = OpenAI()

def review_code(code: str, language: str):
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{
                "role": "user",
                "content": f"Review this {language} code:\n{code}"
            }],
            temperature=0.3,
        )
        return response.choices[0].message.content

    except RateLimitError:
        return "⚠️ AI review skipped (quota exceeded)"