import requests
from bot.config_reader import env_config
import time

token = env_config.tg_token.get_secret_value()

next_update_id = 0

while True:
    response = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates?offset={next_update_id}"
    )
    json = response.json()
    print(json)
    updates = json["result"]

    if updates:
        for update in updates:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]
            message_id = update["message"]["message_id"]
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "reply_parameters": {"message_id": message_id},
                },
            )
            next_update_id = int(update["update_id"])
        next_update_id += 1

    time.sleep(5)
