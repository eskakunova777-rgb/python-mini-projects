import tkinter as tk

from gui import ReminderApp


def main():
    root = tk.Tk()
    app = ReminderApp(root)
    app.run()


if __name__ == "__main__":
    main()
