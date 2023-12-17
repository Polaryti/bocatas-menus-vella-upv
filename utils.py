import json

import pandas as pd

from variables import BOCATAS_SCORE_DATASET

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
