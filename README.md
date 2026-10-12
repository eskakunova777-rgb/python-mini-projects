# Мини-проекты на Python

Три небольшие программы, сделанные в Claude Code на курсе «Вайбкодер» (Zerocoder). Каждая решает одну бытовую задачу и запускается одной командой.

| Проект | Какую задачу решает | Стек |
|---|---|---|
| [calendar-organizer](calendar-organizer/) | Список дел в простой таблице превращается в события календаря с повторами и напоминаниями. Телефон и компьютер напоминают сами | Python 3, только стандартная библиотека, формат iCalendar |
| [reminder-app](reminder-app/) | Окно с напоминаниями: заголовок, описание, время кнопками или вручную, статусы и фильтр | Python 3, Tkinter, SQLite |
| [password-manager](password-manager/) | Хранилище паролей в терминале: вход по мастер-паролю, записи зашифрованы | Python 3, cryptography (Fernet), SQLite |

## Для кого
Для одного человека на своём компьютере. Данные хранятся локально и в сеть не уходят.

## Как запустить

Органайзер:
```bash
cd calendar-organizer
python3 organizer.py
```
Программа читает `dela.csv` и создаёт `napominaniya.ics`. Файл открывается двойным щелчком и добавляется в Календарь. В `dela.csv` лежит пример, замените строки своими делами.

Напоминалка:
```bash
cd reminder-app
python3 main.py
```

Хранилище паролей:
```bash
cd password-manager
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python password_manager.py
```

Базы данных, файл ключа и готовый календарь в репозиторий не попадают: они создаются при первом запуске.
