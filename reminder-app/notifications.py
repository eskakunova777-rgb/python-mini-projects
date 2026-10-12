import threading
import time
import tkinter as tk

try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False


class NotificationManager:
    def __init__(self, db, root, on_shown=None):
        self.db = db
        self.root = root
        self.on_shown = on_shown
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _monitor_loop(self):
        while self._running:
            self.db.mark_overdue()
            due = self.db.get_due_reminders()
            for reminder in due:
                self.root.after(0, self._show_notification, reminder)
            time.sleep(1)

    def _show_notification(self, reminder):
        shown = False
        if PLYER_AVAILABLE:
            try:
                plyer_notification.notify(
                    title=reminder["title"],
                    message=reminder["description"] or "",
                    timeout=10,
                )
                shown = True
            except Exception:
                shown = False

        if not shown:
            self._show_popup(reminder["title"], reminder["description"])

        if reminder["id"] != -1:
            self.db.update_status(reminder["id"], "Готово")
        if self.on_shown:
            self.on_shown()

    def _show_popup(self, title, description):
        popup = tk.Toplevel(self.root)
        popup.title("Напоминание")
        popup.attributes("-topmost", True)
        popup.geometry("360x160")

        tk.Label(popup, text=title, font=("Segoe UI", 13, "bold"), wraplength=320).pack(
            pady=(15, 5), padx=15
        )
        tk.Label(popup, text=description or "", wraplength=320).pack(padx=15)
        tk.Button(popup, text="Ок", command=popup.destroy).pack(pady=15)

        popup.focus_force()
        popup.after(30000, popup.destroy)

    def show_manual_notification(self, reminder_id):
        reminder = self.db.get_reminder_by_id(reminder_id)
        if reminder:
            self._show_notification(reminder)

    def test_notification(self):
        self._show_notification(
            {
                "id": -1,
                "title": "ТЕСТ — Напоминание",
                "description": "Это тестовое напоминание для проверки уведомлений.",
            }
        )
