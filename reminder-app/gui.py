import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from database import ReminderDatabase
from notifications import NotificationManager

STATUS_COLORS = {
    "Готово": "#d4edda",
    "Просрочено": "#f8d7da",
    "Отменено": "#e2e3e5",
    "Ожидает": "#ffffff",
}


class ReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Напоминалка")
        self.root.geometry("760x620")

        self.db = ReminderDatabase()
        self.notifier = NotificationManager(self.db, self.root, on_shown=self.refresh_reminders)

        self.setup_ui()
        self.refresh_reminders()

        self.notifier.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        tk.Label(self.root, text="Напоминалка", font=("Segoe UI", 18, "bold")).pack(pady=15)

        form = tk.LabelFrame(self.root, text="Добавить новое напоминание", padx=10, pady=10)
        form.pack(fill="x", padx=15, pady=5)

        tk.Label(form, text="Заголовок:").grid(row=0, column=0, sticky="w", pady=3)
        self.title_entry = tk.Entry(form, width=60)
        self.title_entry.grid(row=0, column=1, sticky="we", pady=3)

        tk.Label(form, text="Описание:").grid(row=1, column=0, sticky="w", pady=3)
        self.desc_entry = tk.Entry(form, width=60)
        self.desc_entry.grid(row=1, column=1, sticky="we", pady=3)

        tk.Label(form, text="Дата и время:").grid(row=2, column=0, sticky="w", pady=3)
        quick_frame = tk.Frame(form)
        quick_frame.grid(row=2, column=1, sticky="w", pady=3)
        for label, minutes in [
            ("Через 1 мин", 1),
            ("Через 5 мин", 5),
            ("Через 15 мин", 15),
            ("Через 30 мин", 30),
            ("Через 1 час", 60),
        ]:
            tk.Button(
                quick_frame, text=label, command=lambda m=minutes: self.set_quick_time(m)
            ).pack(side="left", padx=2)

        self.datetime_entry = tk.Entry(form, width=60)
        self.datetime_entry.grid(row=3, column=1, sticky="we", pady=3)
        self.set_quick_time(5)

        form.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Добавить напоминание", command=self.add_reminder).pack(
            side="left", padx=5
        )
        tk.Button(btn_frame, text="Тест уведомления", command=self.notifier.test_notification).pack(
            side="left", padx=5
        )

        filter_frame = tk.Frame(self.root)
        filter_frame.pack(fill="x", padx=15, pady=5)
        tk.Label(filter_frame, text="Фильтр по статусу:").pack(side="left")
        self.status_var = tk.StringVar(value="Все")
        status_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.status_var,
            values=["Все", "Ожидает", "Готово", "Просрочено", "Отменено"],
            state="readonly",
            width=15,
        )
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_reminders())
        tk.Button(filter_frame, text="Обновить", command=self.refresh_reminders).pack(
            side="left", padx=5
        )

        self.status_bar_var = tk.StringVar()
        tk.Label(filter_frame, textvariable=self.status_bar_var).pack(side="right")

        list_frame = tk.LabelFrame(self.root, text="Список напоминаний", padx=5, pady=5)
        list_frame.pack(fill="both", expand=True, padx=15, pady=10)

        columns = ("id", "title", "description", "due_at", "status", "created_at")
        headers = ("ID", "Заголовок", "Описание", "Дата/Время", "Статус", "Создано")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        for col, head in zip(columns, headers):
            self.tree.heading(col, text=head)
            width = 60 if col == "id" else 120
            self.tree.column(col, width=width)

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        for status, color in STATUS_COLORS.items():
            self.tree.tag_configure(status, background=color)

        self.tree.bind("<Double-1>", self.on_double_click)

        action_frame = tk.Frame(self.root)
        action_frame.pack(pady=8)
        tk.Button(action_frame, text="Отметить готовым", command=self.mark_as_done).pack(
            side="left", padx=5
        )
        tk.Button(action_frame, text="Удалить", command=self.delete_reminder).pack(
            side="left", padx=5
        )

    def set_quick_time(self, minutes):
        target = datetime.now() + timedelta(minutes=minutes)
        self.datetime_entry.delete(0, tk.END)
        self.datetime_entry.insert(0, target.strftime("%Y-%m-%d %H:%M"))

    def add_reminder(self):
        title = self.title_entry.get().strip()
        description = self.desc_entry.get().strip()
        due_at = self.datetime_entry.get().strip()

        if not title:
            messagebox.showwarning("Ошибка", "Введите заголовок напоминания.")
            return

        try:
            datetime.strptime(due_at, "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showwarning("Ошибка", "Дата должна быть в формате ГГГГ-ММ-ДД ЧЧ:ММ.")
            return

        self.db.add_reminder(title, description, due_at)
        self.title_entry.delete(0, tk.END)
        self.desc_entry.delete(0, tk.END)
        self.refresh_reminders()

    def refresh_reminders(self):
        self.db.mark_overdue()
        for row in self.tree.get_children():
            self.tree.delete(row)

        status_filter = self.status_var.get()
        reminders = self.db.sort_by_due_time(self.db.get_all_reminders(status_filter))
        for r in reminders:
            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(r["id"], r["title"], r["description"], r["due_at"], r["status"], r["created_at"]),
                tags=(r["status"],),
            )

        counts = self.db.get_reminders_count()
        self.status_bar_var.set(
            f"Всего: {counts['Всего']} | Ожидает: {counts['Ожидает']} | "
            f"Готово: {counts['Готово']} | Просрочено: {counts['Просрочено']}"
        )

    def _selected_id(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Напоминание", "Выберите запись в списке.")
            return None
        return int(selection[0])

    def mark_as_done(self):
        reminder_id = self._selected_id()
        if reminder_id is None:
            return
        self.db.update_status(reminder_id, "Готово")
        self.refresh_reminders()

    def delete_reminder(self):
        reminder_id = self._selected_id()
        if reminder_id is None:
            return
        if messagebox.askyesno("Удалить", "Удалить выбранное напоминание?"):
            self.db.delete_reminder(reminder_id)
            self.refresh_reminders()

    def on_double_click(self, event):
        reminder_id = self._selected_id()
        if reminder_id is None:
            return
        r = self.db.get_reminder_by_id(reminder_id)
        if r:
            messagebox.showinfo(
                r["title"],
                f"Описание: {r['description']}\n"
                f"Дата/время: {r['due_at']}\n"
                f"Статус: {r['status']}\n"
                f"Создано: {r['created_at']}",
            )

    def on_closing(self):
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            self.notifier.stop()
            self.root.destroy()

    def run(self):
        self.root.mainloop()
