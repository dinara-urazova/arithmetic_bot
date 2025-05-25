import requests
from bot.config_reader import env_config
import time

token = env_config.tg_token.get_secret_value()


def delete_webhook():  # сбоит без этой функции через какое-то время
    API = f"https://api.telegram.org/bot{token}"
    resp = requests.get(f"{API}/deleteWebhook")
    data = resp.json()
    if data.get("ok"):
        print("Webhook deleted successfully.")
    else:
        print("Failed to delete webhook:", data)


delete_webhook()
next_update_id = 0
users = {}

while True:
    try:  # ask Telegram for new updates
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={
                "offset": next_update_id,
                "timeout": 10,
            },  # Telegram waits up to 10 sec to return updates (server side wait)
        )

        data = response.json()  # process received updates
        print(data)
        updates = data["result"]

        for update in updates:
            next_update_id = update["update_id"] + 1
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]

            if chat_id not in users:
                users[chat_id] = {"step": "ask_first"}

            state = users[chat_id]

            if text == "/start":
                users[chat_id] = {"step": "ask_first"}
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "Добро пожаловать! Пожалуйста, введите первое число.",
                    },
                )

            elif state["step"] == "ask_first":
                try:
                    first_number = float(text)
                    state["first_num"] = first_number
                    state["step"] = "ask_second"
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": "Принял, спасибо! Можете вводить второе число.",
                        },
                    )
                except ValueError:
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": "Пожалуйста, введите число в правильном формате.",
                        },
                    )

            elif state["step"] == "ask_second":
                try:
                    second_number = float(text)
                    total_sum = state["first_num"] + second_number
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": f"Спасибо, принял! Сумма двух чисел - {total_sum}",
                        },
                    )
                    # users = {12345: {'step': 'ask_second', 'first_num': 3.0}} - так выглядит словарь users после запроса 2 числа
                    del users[
                        chat_id
                    ]  # удаляем данные о пользователе, чтобы мб заново ввести числа, словарь пустой -> users = {}
                except ValueError:
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": "Пожалуйста, введите число в правильном формате.",
                        },
                    )
    except Exception as e:
        print(f"The error is {e}")

    time.sleep(5)  # pause locally before next getUpdates request (client side wait)
