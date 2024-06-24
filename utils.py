import json

import pandas as pd
import requests


from variables import (
    BOT_CHAT_ID_BOCATAS,
    BOT_CHAT_ID_DEBUG,
    BOT_CHAT_ID_MENUS,
    BOT_TOKEN,
    BOCATAS_SCORE_DATASET,
)

DEBUG = False
BOCATAS_JSON = "data/bocatas.json" if not DEBUG else "data/bocatas-debug.json"


def get_scores(url):
    df = pd.read_csv(url)
    means = df.mean()
    counts = df.count()
    counts = counts.drop("Marca temporal")
    return pd.concat([means, counts], axis=1, keys=["score", "count"])


def update_scores(scores: pd.DataFrame):
    with open(BOCATAS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    for key, value in scores.iterrows():
        if value["count"] > 0:
            points = f"{str(round(value['score'], 1))} ({str(int(value['count']))})"
            print(points)
            key = key.strip()
            if key in data:
                data[key]["score"] = points
            else:
                print("CLAVE ERRONEA:", key, "/", points)

    json_object = json.dumps(data, indent=4)
    with open(BOCATAS_JSON, "w", encoding="utf-8") as f:
        f.write(json_object)


def download_update_scores():
    scores = get_scores(BOCATAS_SCORE_DATASET)
    update_scores(scores)


def bot_send_text(bot_message, menu):
    if DEBUG:
        BOT_CHAT_ID = BOT_CHAT_ID_DEBUG
    else:
        BOT_CHAT_ID = BOT_CHAT_ID_BOCATAS if menu == 0 else BOT_CHAT_ID_MENUS
    bot_token = BOT_TOKEN
    send_text = (
        "https://api.telegram.org/bot"
        + bot_token
        + "/sendMessage?chat_id="
        + BOT_CHAT_ID
        + "&parse_mode=Markdown&text="
        + bot_message
    )

    response = requests.get(send_text)

    return response


if __name__ == "__main__":
    # msg ='ATENCIÓN: A partir de ahora, los bocatas con "loganiza campera" y "longaniza criolla" aparecerán como "loganiza especial".'
    # bot_send_text(msg, 0)
    download_update_scores()
