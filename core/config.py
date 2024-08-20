from decouple import config, UndefinedValueError
import json

try:
    BOT_TOKEN = config("BOT_TOKEN")
    LOGGING_LEVEL = config("LOGGING_LEVEL")
    ADMIN_ID = int(config("ADMIN_ID"))
    ALLOWED_CHATS = set(json.loads(config("ALLOWED_CHATS")))
except Exception as err:
    if isinstance(err, UndefinedValueError):
        missing_variable = err.args[0].split()[0]
        print(f'Missing "{missing_variable}" in .env')
    if isinstance(err, json.JSONDecodeError):
        print(f"Invalid JSON-syntax in .env")
    if isinstance(err, ValueError):
        print(f"Failed to parse an integer in .env")
