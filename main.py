import datetime
import json
import re
import time
from datetime import date

import requests
import schedule
from PyPDF2 import PdfReader

from utils import download_update_scores
from variables import (BOT_CHAT_ID_BOCATAS, BOT_CHAT_ID_DEBUG,
                       BOT_CHAT_ID_MENUS, BOT_TOKEN)

DEBUG = False
BOCATAS_JSON = "data/bocatas.json" if not DEBUG else "data/bocatas-debug.json"
MENU_JSON = "data/menus.json" if not DEBUG else "data/menus-debug.json"
PERIOD = 60 if not DEBUG else 10

FROM_NUMBER_TO_WEEK_DAY = {
    0: "lunes",
    1: "martes",
    2: "miercoles",
    3: "jueves",
    4: "viernes",
    5: "sabado",
    6: "domingo"
}

FROM_NUMBER_TO_MENU = {
    0: "Bocadillo",
    1: "Menu_normal",
    2: "Menu_integral"
}


def download_pdf(menu: int):
    menu = FROM_NUMBER_TO_MENU[menu] + ".pdf"
    url = "http://www.lavella.es/doc/" + menu
    response = requests.get(url)

    with open(menu, 'wb') as f:
        f.write(response.content)


def get_json_day(menu):
    json_file = BOCATAS_JSON if menu == 0 else MENU_JSON
    with open(json_file, encoding='utf-8') as f:
        data = json.load(f)
        return data["last_day"] if menu == 0 else data[str(menu) + "_last_day"]


def is_necessary_send_update(pdf_date, menu):
    if DEBUG:
        return True
    json_date = list(map(int, get_json_day(menu).split("-")))
    today_date = list(
        map(int, date.today().strftime("%d-%m-%Y").split("-")))
    pdf_date = list(map(int, pdf_date.split("-")))
    if pdf_date[2] < 2000:
        pdf_date[2] += 2000
    if json_date[2] < 2000:
        json_date[2] += 2000

    return json_date != pdf_date and pdf_date == today_date


def platos_name_corrector(plato_name):
    res = re.sub("\s+", " ", plato_name)
    res = res.lower()

    # Casos especiales
    res = res.replace("s alsa", "salsa")
    res = res.replace("c hampiñon", "champiñon")
    res = res.replace("salteada s", "salteadas")
    res = res.replace("verdu ras", "verduras")
    res = res.replace("cordó n", "cordón")

    return res.capitalize()


def platos_data_extractor(menu):
    # PDF data extraction
    reader = PdfReader(FROM_NUMBER_TO_MENU[menu] + ".pdf")
    page = reader.pages[0]
    text = page.extract_text()

    pdf_date = None
    platos = [[], [], []]
    menu_delimiter_count = 0
    for line in text.split("\n"):
        if pdf_date is None and "-" in line:
            pdf_date = line.split()[0]
        elif "*" in line:
            menu_delimiter_count += 1
        elif menu_delimiter_count == 3:
            return pdf_date, [[platos_name_corrector(plato) for plato in platos[0]], [platos_name_corrector(plato) for plato in platos[1]], [platos_name_corrector(plato) for plato in platos[2]]]
        elif 'o ' != line and pdf_date is not None:
            aux = line.replace(",", "")
            if (any(x.isalpha() for x in aux)
                and any(x.isspace() for x in aux)
                    and all(x.isalpha() or x.isspace() for x in aux)):
                platos[menu_delimiter_count].append(line.strip())


def bocate_name_corrector(bocata_name):
    res = re.sub("\s+", " ", bocata_name)
    res = res.lower()

    # Caracteres especiales
    res = res.replace("( ", "(")
    res = res.replace(" )", ")")

    # Corrección de ingredientes
    res = res.replace("a nchoa", "anchoa")
    res = res.replace("anc hoa", "anchoa")
    res = res.replace("pastor", "pastor:")
    res = res.replace("longani za", "longaniza")
    res = res.replace("ma honesa", "mahonesa")
    res = res.replace("pata tas", "patatas")
    res = res.replace("atú n", "atún")
    res = res.replace("hu evo", "huevo")
    res = res.replace("a rodaja ", "a rodajas")

    # Normalización de bocatas
    res = res.replace("tomate a rodajas y aceite", "tomate a rodajas")
    res = res.replace("secreto iberico", "secreto")
    res = res.replace("secreto plancha", "secreto")
    res = res.replace("secreto a la plancha", "secreto")
    res = res.replace("ternera plancha", "ternera")
    res = res.replace("ternera a la plancha", "ternera")
    res = res.replace("blanco y negro", "blanc i negre")
    res = res.replace("calamares romana", "calamares a la romana")
    res = res.replace("longanizas camperas", "longaniza campera")
    res = res.replace("longanizas criolla", "longaniza campera")
    res = res.replace("criolla o campera", "campera")
    res = res.replace("tortilla de ", "tortilla")

    # Normalización de ingredientes
    res = res.replace("all i oli", "allioli")
    res = res.replace("all y oli", "allioli")
    res = res.replace("ajoaceite", "allioli")
    res = res.replace("ajo aceite", "allioli")
    res = res.replace("alioli", "allioli")
    res = res.replace("jamon", "jamón")
    res = res.replace("calabacin", "calabacín")
    res = res.replace("jamón york", "jamón York")
    res = res.replace("bacon", "bacón")
    res = res.replace("mahonesa", "mayonesa")

    # Casos muy especiales
    if "palleter" in res:
        res = "tortilla palleter (jamón serrano y atún)"
    elif "pastor" in res:
        res = "pastor (jamón plancha huevo frito y patatas a lo pobre)"
    elif "esgarraet" in res:
        res = "esgarraet (pimiento, bacalao, ajos y aceite)"
    
    return res.capitalize()


def bocatas_data_extractor():
    # PDF data extraction
    reader = PdfReader(FROM_NUMBER_TO_MENU[0] + ".pdf")
    page = reader.pages[0]
    text = page.extract_text()

    bocatas = []
    prices = []
    i = 0
    for line in text.split("\n"):
        if "-" in line:
            pdf_date = line.strip().split()[1]
        elif "€" in line:
            if "PRECIO" in line:
                prices.append(line.strip().split()[1])
            else:
                prices.append(line.strip().split()[2])
        else:
            aux = line.replace(",", "")
            aux = aux.replace("(", "")
            aux = aux.replace(")", "")
            if (any(x.isalpha() for x in aux)
                and any(x.isspace() for x in aux)
                    and all(x.isalpha() or x.isspace() for x in aux)):
                bocatas.append((line.strip(), i))
            i += 1

    # Bocatas section
    if len(bocatas) == 2:
        bocatas = [bocatas[0][0], bocatas[1][0]]
    elif len(bocatas) == 4:
        bocatas = [bocatas[0][0] + " " + bocatas[1]
                   [0], bocatas[2][0] + " " + bocatas[3][0]]
    elif len(bocatas) == 3:
        if bocatas[0][1] == bocatas[1][1] - 1:
            bocatas = [bocatas[0][0] + " " + bocatas[1][0], bocatas[2][0]]
        else:
            bocatas = [bocatas[0][0], bocatas[1][0] + " " + bocatas[2][0]]
    else:
        bocatas = []

    return pdf_date, [bocate_name_corrector(bocata) for bocata in bocatas], prices


def update_bocata_info(bocatas, prices, pdf_today):
    week_day = datetime.datetime.today().weekday()
    flags = {}

    def individual_update(bocata: str, price, data, index):
        diff = 0
        aux_last_day = "POR PRIMERA VEZ HOY"
        aux_last_price = price

        if bocata not in data:
            data[bocata] = {
                "last_day": pdf_today,
                "last_price": price,
                "frecuency": {
                    "lunes": 0,
                    "martes": 0,
                    "miercoles": 0,
                    "jueves": 0,
                    "viernes": 0,
                    "sabado": 0,
                    "domingo": 0
                },
                "score": -1,
                "count": 1,
                "img": ""
            }

            data[bocata]["frecuency"][FROM_NUMBER_TO_WEEK_DAY[week_day]] = 1
        else:
            if float(data[bocata]["last_price"].replace(",", ".")) > float(price.replace(",", ".")):
                diff = float(data[bocata]["last_price"].replace(",", ".")) - float(price.replace(",", "."))
            else:
                diff = float(price.replace(",", ".")) - float(data[bocata]["last_price"].replace(",", "."))
            aux_last_day = data[bocata]["last_day"]
            aux_last_price = data[bocata]["last_price"]
            data[bocata]["last_day"] = pdf_today
            data[bocata]["last_price"] = price
            data[bocata]["frecuency"][FROM_NUMBER_TO_WEEK_DAY[week_day]] = int(
                data[bocata]["frecuency"][FROM_NUMBER_TO_WEEK_DAY[week_day]]) + 1
            data[bocata]["count"] = data[bocata]["count"] + 1

        flags[str(index) + "_last_day"] = aux_last_day
        flags[str(index) + "_last_price"] = aux_last_price
        flags[str(index) + "_diff"] = diff

    with open(BOCATAS_JSON, encoding='utf-8') as f:
        data = json.load(f)

    data["last_day"] = pdf_today

    for i in range(len(bocatas)):
        individual_update(bocatas[i], prices[i], data, i)

    json_object = json.dumps(data, indent=4)
    with open(BOCATAS_JSON, "w", encoding='utf-8') as f:
        f.write(json_object)

    for i in range(len(bocatas)):
        data[bocatas[i]]['last_day'] = flags[str(i) + "_last_day"]
        data[bocatas[i]]['last_price'] = flags[str(i) + "_last_price"]
        data[bocatas[i]]['diff'] = flags[str(i) + "_diff"]

    return data[bocatas[0]], data[bocatas[1]]


def add_bocata_entry(bocata_name, bocata_data: dict, today):
    data = ["\"" + bocata_name + "\"",
            str(bocata_data["last_price"]).replace(",", "."), "\"" + today + "\""]
    with open("data/bocata-data.csv", "a") as myBOCATAS_FILE:
        myBOCATAS_FILE.write(",".join(data) + "\n")


def check_menu(menu):
    pdf_date, platos = platos_data_extractor(menu)

    if not is_necessary_send_update(pdf_date, menu):
        return -1

    with open(MENU_JSON, encoding='utf-8', mode="r") as f:
        data = json.load(f)
        data[str(menu) + "_last_day"] = pdf_date
    with open(MENU_JSON, encoding='utf-8', mode="w") as f:
        json_object = json.dumps(data, indent=4)
        f.write(json_object)

    res = ""
    res += f"*({pdf_date})*\n\n"

    if menu == 1:
        res += "*MENÚ DEL DÍA*\n\n"
    else:
        res += "*MENÚ DE RÉGIMEN*\n\n"

    # Primer plato
    res += "*PRIMEROS*\n"
    for plato in platos[0]:
        res += f"{plato.lower().capitalize()}\n"
    res += "\n"

    # Segundo plato
    res += "*SEGUNDOS*\n"
    for plato in platos[1]:
        res += f"{plato.lower().capitalize()}\n"
    res += "\n"

    # Postre
    res += "*POSTRES*\n"
    for plato in platos[2]:
        res += f"{plato.lower().capitalize()}\n"

    print(res)
    return res


def check_bocatas():
    pdf_date, bocatas, prices = bocatas_data_extractor()

    if not is_necessary_send_update(pdf_date, 0):
        return -1

    bocata_data_one, bocata_data_two = update_bocata_info(
        bocatas, prices, pdf_date)
    if not DEBUG:
        add_bocata_entry(bocatas[0], bocata_data_one, pdf_date)
        add_bocata_entry(bocatas[1], bocata_data_two, pdf_date)
        download_update_scores()

    res = ""
    res += f"*({pdf_date})*\n\n"
    res += f"*{bocatas[0]}*\n"
    res += f"*Precio:* {prices[0]} €\n"
    if bocata_data_one["diff"] != 0:
        res += f"*ATENCIÓN*: ha sufrido un cambio de {round(bocata_data_one['diff'], 2)} € en su precio.\n"
    if bocata_data_one["img"] != "":
        res += f"*Foto:* {bocata_data_one['img']}\n"
    if bocata_data_one["score"] != -1:
        res += f"*Puntuación:* {bocata_data_one['score']}\n"
    res += f"*Última vez:* {bocata_data_one['last_day']}\n\n"

    res += f"*{bocatas[1]}*\n"
    res += f"*Precio:* {prices[1]} €\n"
    if bocata_data_two["diff"] != 0:
        res += f"*ATENCIÓN*: ha sufrido un cambio de {round(bocata_data_two['diff'], 2)} € en su precio.\n"
    if bocata_data_two["img"] != "":
        res += f"*Foto:* {bocata_data_two['img']}\n"
    if bocata_data_two["score"] != -1:
        res += f"*Puntuación:* {bocata_data_two['score']}\n"
    res += f"*Última vez:* {bocata_data_two['last_day']}\n\n"

    print(res)
    return res


def bot_send_text(bot_message, menu):
    if DEBUG:
        BOT_CHAT_ID = BOT_CHAT_ID_DEBUG
    else:
        BOT_CHAT_ID = BOT_CHAT_ID_BOCATAS if menu == 0 else BOT_CHAT_ID_MENUS
    bot_token = BOT_TOKEN
    send_text = 'https://api.telegram.org/bot' + bot_token + \
        '/sendMessage?chat_id=' + BOT_CHAT_ID + \
        '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)

    return response


def wrapper(menu):
    try:
        download_pdf(menu)
        if menu == 0:
            res = check_bocatas()
        else:
            res = check_menu(menu)
        bot_send_text(res, menu) if res != -1 else None
    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    schedule.every(PERIOD).seconds.do(wrapper, 0)
    schedule.every(PERIOD).seconds.do(wrapper, 1)
    schedule.every(PERIOD).seconds.do(wrapper, 2)

    while True:
        schedule.run_pending()
        time.sleep(1)
