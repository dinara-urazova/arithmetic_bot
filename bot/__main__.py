import requests
import json
from bot.config_reader import env_config
import time

token = env_config.telegram_token.get_secret_value()
OPERATION_SUM = "operation_sum"
OPERATION_SUBSTRACT = "operation_substract"
OPERATION_MULTIPLY = "operation_multiply"
OPERATION_DIVIDE = "operation_divide"

STEP_NEED_FIRST_NUM = "step_need_first_num"
STEP_NEED_OPERATION = "step_need_operation"
STEP_NEED_SECOND_NUM = "step_need_second_num"
STEP_COMPLETED = "step_completed"


def keyboard_builder(buttons=[]) -> str:
    if not buttons:
        return
    result = []
    for text, callback_data in buttons:
        result.append({
            "text": text,
            "callback_data": callback_data,
        }
        )

    return json.dumps(
        {"inline_keyboard": [result]}
    )

def apply_operation(a, b, operation):
    if operation == OPERATION_SUM:
        return a + b
    if operation == OPERATION_SUBSTRACT:
        return a - b 
    if operation == OPERATION_MULTIPLY:
        return a * b
    if operation == OPERATION_DIVIDE:
        return a / b
    
def send_message(chat_id, text, buttons=[]):
    params = {
        "chat_id": chat_id,
        "text": text,
    }
    keyboard = keyboard_builder(buttons)
    if keyboard:
        params["reply_markup"] = keyboard

    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        params=params
    )
  
user_state = {}

def process_update_message(message: dict):
    text = message.get("text")
    chat_id = message["chat"]["id"]

    if text == "/start":
        user_state[chat_id] = {
            "step": STEP_NEED_FIRST_NUM
        } 
        send_message(chat_id, "Добро пожаловать! Пожалуйста, введите первое число.")
        return

    if chat_id not in user_state:
        send_message(chat_id, "Пожалуйста, введите команду /start")
        return

    state = user_state[chat_id]
    if state["step"] == STEP_NEED_FIRST_NUM:
        try:
            first_number = float(text)
            state["first_num"] = first_number
            state["step"] = STEP_NEED_OPERATION
            send_message(
                chat_id,
                "Принял, спасибо! Выберите операцию.",
                [
                    ("+", OPERATION_SUM),
                    ("-", OPERATION_SUBSTRACT), 
                    ("*", OPERATION_MULTIPLY), 
                    ("/", OPERATION_DIVIDE), 
                ]
            )
        except ValueError:
            send_message(chat_id, "Пожалуйста, введите число в правильном формате.")

    elif state["step"] == STEP_NEED_SECOND_NUM:
        try:
            second_number = float(text)
            state["step"] = STEP_COMPLETED
            result = apply_operation(state["first_num"],second_number, state["operation"])
            
            send_message(chat_id, f"Спасибо, принял! Сумма двух чисел - {result}")
            # users = {12345: {'step': 'ask_second', 'first_num': 3.0}} - так выглядит словарь users после запроса 2 числа
            del user_state[
                chat_id
            ]  # удаляем данные о пользователе, чтобы мб заново ввести числа, словарь пустой -> users = {}
        except ValueError:
            send_message(chat_id, "Пожалуйста, введите число в правильном формате.")


def process_update_callback(callback_query):
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        state = user_state[chat_id]
        state["operation"] = callback_query["data"]
        state["step"] = STEP_NEED_SECOND_NUM

        send_message(
                    chat_id,
                    "Принял, спасибо! Введите второе число",
                )
    except Exception as e:
        print(f"👹The error is {repr(e)}")

next_update_id = 0


while True:
    try:  # ask Telegram for new updates
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={
                "offset": next_update_id,
            },
        )

        data = response.json()
        print(data)
        updates = data["result"]

        for update in updates:
            next_update_id = update["update_id"] + 1
            if "callback_query" in update:
                process_update_callback(update["callback_query"])
            if "message" in update:
                process_update_message(update["message"])

    except Exception as e:
        print(f"The error is {e}")

    time.sleep(5)  # pause locally before next getUpdates request (client side wait)


"""
  keyboard = [
        [InlineKeyboardButton("Option 1", callback_data='opt1')],
        [InlineKeyboardButton("Option 2", callback_data='opt2')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
"""
