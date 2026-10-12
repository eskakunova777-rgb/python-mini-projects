import sqlite3
from datetime import datetime, timedelta


class ReminderDatabase:
    def __init__(self, db_path="reminders.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_database()

    def init_database(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                due_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Ожидает',
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def add_reminder(self, title, description, due_at):
        created_at = datetime.now().strftime("%d.%m.%Y %H:%M")
        cur = self.conn.execute(
            "INSERT INTO reminders (title, description, due_at, status, created_at) "
            "VALUES (?, ?, ?, 'Ожидает', ?)",
            (title, description, due_at, created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_all_reminders(self, status_filter=None):
        if status_filter and status_filter != "Все":
            rows = self.conn.execute(
                "SELECT * FROM reminders WHERE status = ? ORDER BY due_at",
                (status_filter,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM reminders ORDER BY due_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_due_reminders(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        rows = self.conn.execute(
            "SELECT * FROM reminders WHERE status = 'Ожидает' AND due_at <= ?",
            (now,),
        ).fetchall()
        return [dict(r) for r in rows]

    def sort_by_due_time(self, reminders):
        return sorted(reminders, key=lambda r: r["due_at"])

    def update_status(self, reminder_id, status):
        self.conn.execute(
            "UPDATE reminders SET status = ? WHERE id = ?", (status, reminder_id)
        )
        self.conn.commit()

    def delete_reminder(self, reminder_id):
        self.conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        self.conn.commit()

    def mark_overdue(self):
        threshold = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
        self.conn.execute(
            "UPDATE reminders SET status = 'Просрочено' "
            "WHERE status = 'Ожидает' AND due_at < ?",
            (threshold,),
        )
        self.conn.commit()

    def get_reminder_by_id(self, reminder_id):
        row = self.conn.execute(
            "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_reminders_count(self):
        all_rows = self.get_all_reminders()
        counts = {"Всего": len(all_rows), "Ожидает": 0, "Готово": 0, "Просрочено": 0}
        for r in all_rows:
            if r["status"] in counts:
                counts[r["status"]] += 1
        return counts
