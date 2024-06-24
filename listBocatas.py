import json

with open("data/bocatas.json", encoding="utf-8") as f:
    data = json.load(f)
    print(data.keys())
