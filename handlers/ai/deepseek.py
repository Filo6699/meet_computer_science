from openai import OpenAI
from decouple import config


API_KEY = config("DEEPSEEK_API_KEY", None)

if not API_KEY:
    logging.ERROR("DEEPSEEK_API_KEY is not in `.env`")


class API:
    client = OpenAI(
        base_url="https://api.deepseek.com",
        api_key=API_KEY,
    )
    temperature = 1
    model = "deepseek-chat"

    @classmethod
    def generate_response(cls, history):
        response = cls.client.chat.completions.create(
            model=cls.model,
            messages=history,
            stream=False,
            temperature=cls.temperature,
            max_tokens=200,
        )

        response_text = response.choices[0].message.content

        return response_text
