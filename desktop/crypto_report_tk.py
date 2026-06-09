import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import csv
import json
import os
import hashlib
from datetime import datetime

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import mplcursors

PURPLE = "#6C5CE7"

class CryptoReportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CryptoReport")
        self.root.geometry("1050x780")
        self.current_user = None
        self.current_data = []
        self.build_login_screen()

    def build_login_screen(self):
        self.login_frame = tk.Frame(self.root, bg="#F8F9FA")
        self.login_frame.pack(fill="both", expand=True)

        center = tk.Frame(self.login_frame, bg="#F8F9FA")
        center.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(center, text="CryptoReport", font=("Arial", 32, "bold"), fg=PURPLE).pack(pady=(0, 8))
        tk.Label(center, text="Аналитика криптовалют", font=("Arial", 13), fg="#555555").pack(pady=(0, 35))

        tk.Label(center, text="Имя пользователя").pack(anchor="w")
        self.username_entry = tk.Entry(center, width=34, font=("Arial", 11))
        self.username_entry.pack(pady=(0, 10))

        tk.Label(center, text="Пароль").pack(anchor="w")
        self.password_entry = tk.Entry(center, width=34, font=("Arial", 11), show="*")
        self.password_entry.pack(pady=(0, 25))

        self.username_entry.bind("<Return>", lambda event: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda event: self.login())

        btns = tk.Frame(center)
        btns.pack(pady=10)

        login_btn = ttk.Button(btns, text="Войти", style="Purple.TButton", width=16, command=self.login)
        login_btn.pack(side="left", padx=8)

        reg_btn = ttk.Button(btns, text="Зарегистрироваться", style="Purple.TButton", width=20, command=self.register)
        reg_btn.pack(side="left", padx=8)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if check_login(username, password):
            self.current_user = username
            self.login_frame.destroy()
            self.build_dashboard()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        success, msg = register_user(username, password)
        messagebox.showinfo("Регистрация", msg) if success else messagebox.showerror("Ошибка", msg)

    def build_dashboard(self):
        top = tk.Frame(self.root, bg=PURPLE, height=50)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text=f"CryptoReport  •  {self.current_user}", 
                 bg=PURPLE, fg="white", font=("Arial", 12, "bold")).pack(side="left", padx=20, pady=12)

        tk.Button(top, text="Выйти", bg="#c0392b", fg="white", command=self.logout).pack(side="right", padx=15, pady=10)

        form = tk.LabelFrame(self.root, text="Запрос данных", padx=15, pady=12)
        form.pack(fill="x", padx=20, pady=10)

        tk.Label(form, text="Криптовалюта:").grid(row=0, column=0)
        self.coin_var = tk.StringVar(value="bitcoin")
        ttk.Combobox(form, textvariable=self.coin_var, values=list(COINS.keys()), state="readonly", width=18).grid(row=0, column=1, padx=8)

        tk.Label(form, text="Период:").grid(row=0, column=2, padx=(15, 0))
        self.period_var = tk.IntVar(value=7)
        ttk.Combobox(form, textvariable=self.period_var, values=list(PERIODS.keys()), state="readonly", width=16).grid(row=0, column=3, padx=8)

        ttk.Button(form, text="Получить данные", style="Purple.TButton",
                   command=self.fetch_data).grid(row=0, column=4, padx=20)

        result = tk.LabelFrame(self.root, text="Результаты и график", padx=10, pady=10)
        result.pack(fill="both", expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(result, columns=("Дата", "Цена"), show="headings", height=6)
        self.tree.heading("Дата", text="Дата")
        self.tree.heading("Цена", text="Цена (USD)")
        self.tree.pack(fill="x", pady=5)

        self.fig = Figure(figsize=(9, 3.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=result)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=8)

        ttk.Button(result, text="Сохранить отчёт в CSV",
                   command=self.save_csv).pack(pady=5)

    def fetch_data(self):
        coin = self.coin_var.get()
        days = self.period_var.get()

        data, error = fetch_crypto_data(coin, days)
        if error:
            messagebox.showerror("Ошибка", error)
            return

        self.current_data = data

        for i in self.tree.get_children():
            self.tree.delete(i)
        for row in data:
            self.tree.insert("", "end", values=(row["date"], row["price"]))

        # === ГРАФИК С ПОДСКАЗКАМИ ===
        self.ax.clear()
        dates = [d["date"] for d in data]
        prices = [d["price"] for d in data]

        line, = self.ax.plot(dates, prices, color=PURPLE, linewidth=2.2, marker="o", markersize=4)
        self.ax.fill_between(dates, prices, alpha=0.12, color=PURPLE)
        self.ax.set_title(f"{COINS[coin]} — Цена за {days} дней", fontsize=11, pad=8)
        self.ax.set_ylabel("Цена (USD)")

        self.ax.xaxis.set_major_locator(plt.MaxNLocator(7))
        self.ax.tick_params(axis='x', rotation=45, labelsize=7)

        self.fig.tight_layout()
        self.canvas.draw_idle()

        # Всплывающие подсказки
        cursor = mplcursors.cursor(line, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(
            f"{sel.target[0]:.0f}\n{sel.target[1]:.2f} USD"
        ))

    def save_csv(self):
        if not self.current_data:
            messagebox.showwarning("Нет данных", "Сначала получите данные")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV файлы", "*.csv")],
            initialfile=f"CryptoReport_{self.coin_var.get()}_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if filename:
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Дата", "Цена USD"])
                for row in self.current_data:
                    writer.writerow([row["date"], row["price"]])
            messagebox.showinfo("Готово", f"Отчёт сохранён:\n{filename}")

    def logout(self):
        self.root.destroy()
        import sys, os
        os.execv(sys.executable, ['python'] + sys.argv)


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def load_users():
    if not os.path.exists("users.json"):
        demo = {"student": hashlib.sha256("123456".encode()).hexdigest()}
        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(demo, f, indent=2)
        return demo
    with open("users.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    users = load_users()
    return username in users and users[username] == hash_password(password)

def register_user(username, password):
    users = load_users()
    if username in users:
        return False, "Пользователь уже существует"
    if len(password) < 4:
        return False, "Пароль должен быть минимум 4 символа"
    users[username] = hash_password(password)
    save_users(users)
    return True, "Регистрация успешна!"

def fetch_crypto_data(coin_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        prices = data.get("prices", [])
        if not prices:
            return None, "Нет данных"
        result = []
        for timestamp, price in prices:
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
            result.append({"date": date_str, "price": round(price, 2)})
        return result, None
    except Exception as e:
        return None, str(e)


COINS = {
    "bitcoin": "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "solana": "Solana (SOL)",
    "cardano": "Cardano (ADA)",
    "ripple": "Ripple (XRP)",
    "dogecoin": "Dogecoin (DOGE)",
}

PERIODS = {
    7: "7 дней",
    30: "30 дней",
    90: "90 дней",
}


if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoReportApp(root)
    root.mainloop()