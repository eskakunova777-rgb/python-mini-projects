import hashlib
import secrets
import sqlite3
import string
import sys
from getpass import getpass
from pathlib import Path

from cryptography.fernet import Fernet


class DatabaseManager:
    def __init__(self, db_path="passwords.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_database()

    def init_database(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS master (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password_hash TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                login TEXT,
                password_encrypted TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def set_master_password(self, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.conn.execute(
            "INSERT OR REPLACE INTO master (id, password_hash) VALUES (1, ?)",
            (password_hash,),
        )
        self.conn.commit()

    def get_master_password(self):
        row = self.conn.execute("SELECT password_hash FROM master WHERE id = 1").fetchone()
        return row["password_hash"] if row else None

    def add_password(self, name, login, encrypted_password):
        self.conn.execute(
            "INSERT OR REPLACE INTO passwords (name, login, password_encrypted) "
            "VALUES (?, ?, ?)",
            (name, login, encrypted_password),
        )
        self.conn.commit()

    def get_password(self, name):
        row = self.conn.execute(
            "SELECT * FROM passwords WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None

    def list_passwords(self):
        rows = self.conn.execute("SELECT name, login FROM passwords ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def delete_password(self, name):
        cur = self.conn.execute("DELETE FROM passwords WHERE name = ?", (name,))
        self.conn.commit()
        return cur.rowcount > 0


class EncryptionManager:
    def __init__(self, key_path=".key"):
        self.key_path = Path(key_path)
        if self.key_path.exists():
            self.key = self.key_path.read_bytes()
        else:
            self.key = Fernet.generate_key()
            self.key_path.write_bytes(self.key)
        self.fernet = Fernet(self.key)

    def encrypt(self, plaintext):
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext):
        return self.fernet.decrypt(ciphertext.encode()).decode()


class PasswordGenerator:
    def __init__(self):
        self.db = DatabaseManager()
        self.enc = EncryptionManager()

    def generate_password(
        self,
        length=16,
        use_upper=True,
        use_lower=True,
        use_digits=True,
        use_special=True,
        exclude_similar=False,
    ):
        pools = []
        if use_upper:
            pools.append(string.ascii_uppercase)
        if use_lower:
            pools.append(string.ascii_lowercase)
        if use_digits:
            pools.append(string.digits)
        if use_special:
            pools.append("!@#$%^&*()-_=+")

        if not pools:
            raise ValueError("Нужно выбрать хотя бы один тип символов.")

        alphabet = "".join(pools)
        if exclude_similar:
            similar = "0Ol1I"
            alphabet = "".join(c for c in alphabet if c not in similar)

        password = "".join(secrets.choice(alphabet) for _ in range(length))
        return password

    def setup_master_password(self):
        print("Мастер-пароль не найден. Создаём новый.")
        while True:
            pw1 = getpass("Придумайте мастер-пароль: ")
            pw2 = getpass("Повторите мастер-пароль: ")
            if pw1 != pw2:
                print("Пароли не совпадают, попробуйте снова.\n")
                continue
            if len(pw1) < 4:
                print("Пароль слишком короткий (минимум 4 символа).\n")
                continue
            self.db.set_master_password(pw1)
            print("Мастер-пароль сохранён.\n")
            return

    def authenticate(self):
        stored_hash = self.db.get_master_password()
        if stored_hash is None:
            self.setup_master_password()
            return True

        for attempt in range(3):
            pw = getpass("Введите мастер-пароль: ")
            if hashlib.sha256(pw.encode()).hexdigest() == stored_hash:
                return True
            print(f"Неверный пароль. Осталось попыток: {2 - attempt}\n")
        return False

    def add_password_interactive(self):
        name = input("Название/откуда (например, Google): ").strip()
        if not name:
            print("Название не может быть пустым.\n")
            return
        login = input("Логин: ").strip()

        choice = input("Сгенерировать пароль автоматически? (да/нет): ").strip().lower()
        if choice in ("да", "y", "yes", ""):
            length_raw = input("Длина пароля [16]: ").strip()
            length = int(length_raw) if length_raw.isdigit() else 16
            length = min(max(length, 4), 64)

            exclude = input("Исключить похожие символы 0/O, l/I/1? (да/нет) [нет]: ").strip().lower()
            exclude_similar = exclude in ("да", "y", "yes")

            password = self.generate_password(length=length, exclude_similar=exclude_similar)
            print(f"Сгенерированный пароль: {password}")
        else:
            password = getpass("Введите пароль: ")

        encrypted = self.enc.encrypt(password)
        self.db.add_password(name, login, encrypted)
        print(f"Запись «{name}» сохранена.\n")

    def get_password_interactive(self):
        name = input("Название записи: ").strip()
        record = self.db.get_password(name)
        if not record:
            print(f"Запись «{name}» не найдена.\n")
            return
        password = self.enc.decrypt(record["password_encrypted"])
        print(f"Название: {record['name']}")
        print(f"Логин: {record['login']}")
        print(f"Пароль: {password}\n")

    def list_passwords(self):
        records = self.db.list_passwords()
        if not records:
            print("Записей пока нет.\n")
            return
        print(f"{'Название':<20} {'Логин':<25}")
        print("-" * 45)
        for r in records:
            print(f"{r['name']:<20} {r['login'] or '':<25}")
        print()

    def delete_password_interactive(self):
        name = input("Название записи для удаления: ").strip()
        if self.db.delete_password(name):
            print(f"Запись «{name}» удалена.\n")
        else:
            print(f"Запись «{name}» не найдена.\n")

    def show_menu(self):
        print(
            "\nКоманды: add | get | list | delete | new | exit\n"
            "  add    — добавить новую запись\n"
            "  get    — получить пароль по названию\n"
            "  list   — показать список всех записей\n"
            "  delete — удалить запись по названию\n"
            "  new    — сгенерировать пароль (без сохранения)\n"
            "  exit   — выйти\n"
        )

    def run(self):
        print("=== Менеджер паролей ===\n")
        if not self.authenticate():
            print("Не удалось войти. Выход.")
            sys.exit(1)

        print("Успешный вход.\n")
        self.show_menu()

        while True:
            choice = input("Команда: ").strip().lower()
            if choice == "add":
                self.add_password_interactive()
            elif choice == "get":
                self.get_password_interactive()
            elif choice == "list":
                self.list_passwords()
            elif choice == "delete":
                self.delete_password_interactive()
            elif choice == "new":
                length_raw = input("Длина пароля [16]: ").strip()
                length = int(length_raw) if length_raw.isdigit() else 16
                exclude = input("Исключить похожие символы? (да/нет) [нет]: ").strip().lower()
                exclude_similar = exclude in ("да", "y", "yes")
                print(f"Сгенерированный пароль: {self.generate_password(length=length, exclude_similar=exclude_similar)}\n")
            elif choice in ("exit", "quit", "q"):
                print("До встречи!")
                break
            elif choice == "help":
                self.show_menu()
            else:
                print("Неизвестная команда. Введите help для списка команд.\n")


def main():
    try:
        pm = PasswordGenerator()
        pm.run()
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")


if __name__ == "__main__":
    main()
