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


def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        params={"chat_id": chat_id, "text": text},
    )


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
            if "message" not in update or "text" not in update["message"]:
                next_update_id = update["update_id"] + 1
                continue
            try:  # given the code before we ensure that the message exists and is of 'text' type
                text = update["message"].get("text")
                chat_id = update["message"]["chat"]["id"]

                if text == "/start":
                    users[chat_id] = {"step": "ask_first"} # which means the bot is waiting for the first num from the user with that chat_id
                    send_message(
                        chat_id, "Добро пожаловать! Пожалуйста, введите первое число."
                    )
                    continue 
                    # we skip the code below and move on to the next update from 'for update in updates' (if no updates -> the loop ends and waits for the next getUpdates request. If there are more updates -> it continues to process the next message from the queue.)

                if chat_id not in users:
                    send_message(chat_id, "Пожалуйста, введите команду /start")
                    continue

                state = users[chat_id]
                if state["step"] == "ask_first":
                    try:
                        first_number = float(text)
                        state["first_num"] = first_number
                        state["step"] = "ask_second"
                        send_message(
                            chat_id, "Принял, спасибо! Можете вводить второе число."
                        )
                    except ValueError:
                        send_message(
                            chat_id, "Пожалуйста, введите число в правильном формате."
                        )

                elif state["step"] == "ask_second":
                    try:
                        second_number = float(text)
                        total_sum = state["first_num"] + second_number
                        send_message(
                            chat_id, f"Спасибо, принял! Сумма двух чисел - {total_sum}"
                        )
                        # users = {12345: {'step': 'ask_second', 'first_num': 3.0}} - так выглядит словарь users после запроса 2 числа
                        del users[
                            chat_id
                        ]  # удаляем данные о пользователе, чтобы мб заново ввести числа, словарь пустой -> users = {}
                    except ValueError:
                        send_message(
                            chat_id, "Пожалуйста, введите число в правильном формате."
                        )

            finally:  # increment next_update_id in any way (even if the update message is invalid as we don't want to see them again)
                next_update_id = update["update_id"] + 1

    except Exception as e:
        print(f"The error is {e}")

    time.sleep(5)  # pause locally before next getUpdates request (client side wait)
