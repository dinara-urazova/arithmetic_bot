import requests
import json
from bot.config_reader import env_config
import time
from math import sqrt

token = env_config.telegram_token.get_secret_value()
OPERATION_ADD = "operation_add"
OPERATION_SUBTRACT = "operation_subtract"
OPERATION_MULTIPLY = "operation_multiply"
OPERATION_DIVIDE = "operation_divide"

OPERATION_FIND_SQUARE = "operation_find_square"
OPERATION_FIND_ROOT = "operation_find_root"

STEP_NEED_FIRST_NUM = "step_need_first_num"
STEP_NEED_OPERATION = "step_need_operation"
STEP_NEED_SECOND_NUM = "step_need_second_num"


def keyboard_builder(buttons: list) -> str | None:
    if not buttons:
        return None
    result = []
    for text, callback_data in buttons:
        result.append(
            {
                "text": text,
                "callback_data": callback_data,
            }
        )

    return json.dumps({"inline_keyboard": [result]})


def apply_unary_operation(a: int | float, operation: str) -> float:
    if operation == OPERATION_FIND_SQUARE:
        return f"{a**2:,.2f}"  # shows only 2 nums after comma (.2f) and uses comma as thousands separator (,)
    if operation == OPERATION_FIND_ROOT:
        return f"{sqrt(a):,.2f}"
    raise RuntimeError(f"Unsupported operation: {operation}")


def apply_binary_operation(
    a: int | float, b: int | float, operation: str
) -> int | float:
    if operation == OPERATION_ADD:
        return a + b
    if operation == OPERATION_SUBTRACT:
        return a - b
    if operation == OPERATION_MULTIPLY:
        return a * b
    if operation == OPERATION_DIVIDE:
        return a / b
    raise RuntimeError(f"Unsupported operation: {operation}")


def send_message(chat_id: int, text: str, buttons=None):
    params = {
        "chat_id": chat_id,
        "text": text,
    }
    keyboard = keyboard_builder(buttons)
    if keyboard:
        params["reply_markup"] = keyboard

    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", params=params)


user_state = {}


def process_need_first_num(chat_id: int, text: str, state: dict):
    try:
        first_number = float(text)
        state["first_num"] = first_number
        state["step"] = STEP_NEED_OPERATION
        send_message(
            chat_id,
            "Принял, спасибо! Выберите операцию.",
            [
                ("+", OPERATION_ADD),
                ("-", OPERATION_SUBTRACT),
                ("*", OPERATION_MULTIPLY),
                ("/", OPERATION_DIVIDE),
                ("x²", OPERATION_FIND_SQUARE),
                ("√x", OPERATION_FIND_ROOT),
            ],
        )
    except ValueError:
        send_message(chat_id, "Пожалуйста, введите число в правильном формате.")
    return None


def process_need_second_num(chat_id: int, text: str, state: dict):
    try:
        second_number = float(text)
        result = apply_binary_operation(
            state["first_num"], second_number, state["operation"]
        )

        send_message(chat_id, f"Спасибо, принял! Результат операции - {result}")
        # user_state = {12345: {'step': 'ask_second', 'first_num': 3.0}} - так выглядит словарь users после запроса 2 числа
        del user_state[
            chat_id
        ]  # удаляем данные о пользователе, чтобы мб заново ввести числа, словарь пустой -> user_state = {}
    except ValueError:
        send_message(chat_id, "Пожалуйста, введите число в правильном формате.")
    except ZeroDivisionError:
        send_message(chat_id, "Пожалуйста, введите другое число. На ноль делить нелья.")
    return None


def process_update_message(message: dict) -> None:
    text = str(message.get("text"))
    chat_id = message["chat"]["id"]

    if text == "/start":
        user_state[chat_id] = {"step": STEP_NEED_FIRST_NUM}
        send_message(chat_id, "Добро пожаловать! Пожалуйста, введите первое число.")
        return None

    if chat_id not in user_state:
        send_message(chat_id, "Пожалуйста, введите команду /start")
        return None

    state = user_state[chat_id]  # cловарь (value) при chat_id (key), содержащий user_data

    if state["step"] == STEP_NEED_FIRST_NUM:
        return process_need_first_num(chat_id, text, state)

    if state["step"] == STEP_NEED_SECOND_NUM:
        return process_need_second_num(chat_id, text, state)

    return None


def process_update_callback(callback_query):
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        state = user_state[chat_id]
        state["operation"] = callback_query["data"]
        if state["operation"] in (OPERATION_FIND_ROOT, OPERATION_FIND_SQUARE):
            if state["operation"] == OPERATION_FIND_ROOT and state["first_num"] < 0:
                send_message(
                    chat_id,
                    "Нельзя извлекать корень из отрицательных чисел. Пожалуйста, введите другое число ",
                )
                state["step"] = (
                    STEP_NEED_FIRST_NUM  # сбрасываем на 1 шаг, можно сразу ввести первое число, минуя /start
                )
                return None

            result = apply_unary_operation(state["first_num"], state["operation"])
            send_message(chat_id, f"Спасибо, принял! Результат операции - {result}")
            del user_state[chat_id]
            return None

        else:
            state["step"] = STEP_NEED_SECOND_NUM
            send_message(
                chat_id,
                "Принял, спасибо! Введите второе число",
            )

    except Exception as e:
        print(f"The error is {repr(e)}")


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

    time.sleep(2)
