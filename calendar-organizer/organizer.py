"""Бытовой органайзер: превращает список дел из dela.csv в файл календаря napominaniya.ics.

Запуск: python3 organizer.py
Потом открыть napominaniya.ics двойным щелчком, события попадут в Календарь.
"""

import csv
import hashlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

PAPKA = Path(__file__).parent
VHOD = PAPKA / "dela.csv"
VYHOD = PAPKA / "napominaniya.ics"

POVTORY = {
    "нет": None,
    "каждую неделю": "WEEKLY",
    "каждый месяц": "MONTHLY",
    "каждый год": "YEARLY",
}

# Сколько минут в одной единице из колонки «напомнить за»
EDINICY = {
    "минут": 1, "минута": 1, "минуты": 1, "минуту": 1,
    "час": 60, "часа": 60, "часов": 60,
    "день": 1440, "дня": 1440, "дней": 1440,
}

CHAS_NAPOMINANIYA = 9  # для дел на весь день напоминание приходит в 9:00
DLITELNOST_MIN = 30    # длительность встречи или звонка в календаре


class OshibkaVStroke(Exception):
    pass


def razobrat_napominanie(tekst):
    """«1 день» -> 1440 минут, «30 минут» -> 30, «0» или пусто -> 0."""
    tekst = tekst.strip().lower()
    if tekst in ("", "0", "в момент"):
        return 0
    chasti = tekst.split()
    if len(chasti) != 2 or not chasti[0].isdigit() or chasti[1] not in EDINICY:
        raise OshibkaVStroke(
            f"не понимаю «напомнить за»: «{tekst}». Примеры: 1 день, 2 часа, 30 минут, 0"
        )
    return int(chasti[0]) * EDINICY[chasti[1]]


def trigger(minuty, ves_den):
    """Строка TRIGGER для напоминания."""
    if ves_den:
        # Отсчёт идёт от полуночи дня события: напоминаем в 9:00 за нужное число дней
        if minuty % 1440 != 0:
            raise OshibkaVStroke(
                "для дела без времени «напомнить за» указывается в днях (или 0)"
            )
        sdvig = CHAS_NAPOMINANIYA * 60 - minuty
    else:
        sdvig = -minuty
    znak = "-" if sdvig < 0 else ""
    return f"{znak}PT{abs(sdvig)}M"


def ekran(tekst):
    """Экранирование спецсимволов по правилам формата iCalendar."""
    return (
        tekst.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def perenesti(stroka):
    """Строки длиннее 75 байт переносятся, русские буквы при этом не режутся пополам."""
    kuski, tekushiy, dlina = [], "", 0
    for simvol in stroka:
        ves = len(simvol.encode("utf-8"))
        if dlina + ves > 74:
            kuski.append(tekushiy)
            tekushiy, dlina = " ", 1
        tekushiy += simvol
        dlina += ves
    kuski.append(tekushiy)
    return "\r\n".join(kuski)


def sobytie(delo, nomer):
    chto = delo["что"].strip()
    if not chto:
        raise OshibkaVStroke("пустое название дела")

    try:
        data = datetime.strptime(delo["дата"].strip(), "%d.%m.%Y")
    except ValueError:
        raise OshibkaVStroke(f"дата «{delo['дата']}» должна быть в виде ДД.ММ.ГГГГ")

    vremya = delo["время"].strip()
    ves_den = vremya == ""
    if not ves_den:
        try:
            chasy = datetime.strptime(vremya, "%H:%M")
        except ValueError:
            raise OshibkaVStroke(f"время «{vremya}» должно быть в виде ЧЧ:ММ")
        nachalo = data.replace(hour=chasy.hour, minute=chasy.minute)

    povtor = delo["повтор"].strip().lower() or "нет"
    if povtor not in POVTORY:
        raise OshibkaVStroke(
            f"не понимаю повтор «{povtor}». Варианты: {', '.join(POVTORY)}"
        )

    minuty = razobrat_napominanie(delo["напомнить за"])

    # Один и тот же UID при повторном запуске: календарь обновит событие, а не создаст дубль
    uid = hashlib.sha1(f"{chto}|{delo['дата']}|{vremya}".encode("utf-8")).hexdigest()[:20]

    stroki = [
        "BEGIN:VEVENT",
        f"UID:{uid}@bytovoy-organizer",
        f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ekran(chto)}",
    ]
    if ves_den:
        stroki.append(f"DTSTART;VALUE=DATE:{data.strftime('%Y%m%d')}")
        stroki.append(f"DTEND;VALUE=DATE:{(data + timedelta(days=1)).strftime('%Y%m%d')}")
    else:
        konec = nachalo + timedelta(minutes=DLITELNOST_MIN)
        stroki.append(f"DTSTART:{nachalo.strftime('%Y%m%dT%H%M%S')}")
        stroki.append(f"DTEND:{konec.strftime('%Y%m%dT%H%M%S')}")
    if POVTORY[povtor]:
        stroki.append(f"RRULE:FREQ={POVTORY[povtor]}")
    stroki += [
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{ekran(chto)}",
        f"TRIGGER:{trigger(minuty, ves_den)}",
        "END:VALARM",
        "END:VEVENT",
    ]

    if povtor == "каждый месяц" and data.day > 28:
        print(
            f"  Внимание, строка {nomer}: {data.day}-е число есть не в каждом месяце, "
            "в коротких месяцах событие пропустится."
        )
    return stroki


def main():
    if not VHOD.exists():
        sys.exit(f"Не нашла файл со списком дел: {VHOD}")

    with open(VHOD, encoding="utf-8-sig", newline="") as f:
        dela = list(csv.DictReader(f, delimiter=";"))

    nuzhnye = {"что", "дата", "время", "повтор", "напомнить за"}
    if not dela or not nuzhnye.issubset(dela[0].keys()):
        sys.exit("В dela.csv первая строка должна быть: что;дата;время;повтор;напомнить за")

    stroki = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Bytovoy organizer//RU",
        "CALSCALE:GREGORIAN",
    ]
    gotovo, oshibki = 0, 0
    for nomer, delo in enumerate(dela, start=2):
        try:
            stroki += sobytie(delo, nomer)
            gotovo += 1
            print(f"  + {delo['что'].strip()} ({delo['дата'].strip()})")
        except OshibkaVStroke as e:
            oshibki += 1
            print(f"  ! Строка {nomer} пропущена: {e}")
    stroki.append("END:VCALENDAR")

    if gotovo == 0:
        sys.exit("Ни одного дела не получилось записать, файл календаря не создан.")

    VYHOD.write_bytes(("\r\n".join(perenesti(s) for s in stroki) + "\r\n").encode("utf-8"))
    print(f"\nГотово: дел в календаре {gotovo}, пропущено {oshibki}.")
    print(f"Файл: {VYHOD}")
    print("Откройте его двойным щелчком, чтобы добавить события в Календарь.")


if __name__ == "__main__":
    main()
