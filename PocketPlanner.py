import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime
import os
import shutil
import tempfile

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


# ==========================================================
# DATABASE 
# ==========================================================
DB_PATH = "budget.db"


# ==========================================================
# DATABASE SETUP
# ==========================================================
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    amount REAL,
    type TEXT,
    category TEXT,
    date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    app_pin TEXT,
    security_question TEXT,
    security_answer TEXT,
    monthly_budget REAL
)
""")

conn.commit()

# ---------------- ADD NEW COLUMNS IF NOT EXISTS ---------------- #
cursor.execute("PRAGMA table_info(settings)")
cols = [c[1] for c in cursor.fetchall()]

if "currency" not in cols:
    cursor.execute("ALTER TABLE settings ADD COLUMN currency TEXT DEFAULT 'INR'")
    conn.commit()

# Insert default settings if missing
cursor.execute("SELECT * FROM settings WHERE id=1")
row = cursor.fetchone()

if row is None:
    cursor.execute("""
        INSERT INTO settings (id, app_pin, security_question, security_answer, monthly_budget, currency)
        VALUES (1, ?, ?, ?, ?, ?)
    """, ("1234", "What is your favourite color?", "pink", 0, "INR"))
    conn.commit()


# ==========================================================
# CATEGORY LIST
# ==========================================================
categories_list = [
    "Food 🍔", "Travel 🚗", "Shopping 🛍️",
    "Bills 💡", "Health 💊", "Salary 💼",
    "Education 📚", "Entertainment 🎬",
    "Gifts 🎁", "Other ✨"
]


# ==========================================================
# THEMES
# ==========================================================
LIGHT_THEME = {
    "BG": "#F6F3EE",
    "CARD": "#FFFFFF",
    "TEXT": "#222222",
    "MUTED": "#666666",
    "ACCENT": "#A3B18A",
    "ACCENT2": "#DDBEA9",
    "SIDEBAR": "#EFE7DD",
    "DANGER": "#D62828",
    "PURPLE": "#6D597A",
    "BORDER": "#E5DED4",
    "HEADER": "#FFFFFF",
    "HOVER": "#F1E3D3",
}

DARK_THEME = {
    "BG": "#111111",
    "CARD": "#1E1E1E",
    "TEXT": "#F5F5F5",
    "MUTED": "#AAAAAA",
    "ACCENT": "#6BCB77",
    "ACCENT2": "#FFD93D",
    "SIDEBAR": "#181818",
    "DANGER": "#FF4C4C",
    "PURPLE": "#B388FF",
    "BORDER": "#333333",
    "HEADER": "#1A1A1A",
    "HOVER": "#2B2B2B",
}


# ==========================================================
# ROUNDED BUTTON
# ==========================================================
def rounded_button(parent, text, command, bg, fg, width=220, height=45):
    canvas = tk.Canvas(parent, width=width, height=height,
                       bg=parent["bg"], highlightthickness=0)

    radius = 25

    canvas.create_oval(5, 5, 5 + radius, 5 + radius, fill=bg, outline=bg)
    canvas.create_oval(width - radius - 5, 5, width - 5, 5 + radius, fill=bg, outline=bg)
    canvas.create_rectangle(5 + radius / 2, 5, width - radius / 2 - 5,
                            5 + radius, fill=bg, outline=bg)

    canvas.create_rectangle(5, 5 + radius / 2, width - 5,
                            height - 5, fill=bg, outline=bg)

    text_id = canvas.create_text(width // 2, height // 2,
                                 text=text, fill=fg,
                                 font=("Segoe UI", 12, "bold"))

    def on_click(event):
        command()

    def on_enter(event):
        canvas.itemconfig(text_id, font=("Segoe UI", 12, "bold", "underline"))

    def on_leave(event):
        canvas.itemconfig(text_id, font=("Segoe UI", 12, "bold"))

    canvas.bind("<Button-1>", on_click)
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)

    return canvas


# ==========================================================
# MAIN APP
# ==========================================================
class BudgetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PocketPlanner✨💖")
        self.root.geometry("1350x760")
        self.root.minsize(1250, 700)

        

        self.theme = LIGHT_THEME
        self.is_dark = False
        self.active_btn = None

        self.setup_styles()
        self.setup_ui()
        self.show_dashboard()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- STYLE SETUP ---------------- #
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Treeview",
                        background=self.theme["CARD"],
                        foreground=self.theme["TEXT"],
                        rowheight=30,
                        fieldbackground=self.theme["CARD"],
                        font=("Segoe UI", 10))

        style.configure("Treeview.Heading",
                        background=self.theme["ACCENT2"],
                        foreground=self.theme["TEXT"],
                        font=("Segoe UI", 11, "bold"))

        style.map("Treeview",
                  background=[("selected", self.theme["ACCENT"])])

        style.configure("TCombobox",
                        fieldbackground=self.theme["CARD"],
                        background=self.theme["CARD"],
                        foreground=self.theme["TEXT"])

        style.configure("TNotebook",
                        background=self.theme["BG"],
                        borderwidth=0)

        style.configure("TNotebook.Tab",
                        font=("Segoe UI", 11, "bold"),
                        padding=[10, 6])

    # ---------------- CURRENCY ---------------- #
    def get_currency(self):
        cursor.execute("SELECT currency FROM settings WHERE id=1")
        cur = cursor.fetchone()[0]
        return cur if cur else "INR"

    def set_currency(self, value):
        cursor.execute("UPDATE settings SET currency=? WHERE id=1", (value,))
        conn.commit()

    def format_money(self, amount):
        cur = self.get_currency()
        return f"{cur} {amount:.2f}"

    # ---------------- AUTO BACKUP ON EXIT ---------------- #
    def on_close(self):
        try:
            self.auto_backup()
        except:
            pass
        self.root.destroy()

    def auto_backup(self):
        if not os.path.exists(DB_PATH):
            return

        backup_folder = "AutoBackups"
        os.makedirs(backup_folder, exist_ok=True)

        time_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_file = os.path.join(backup_folder, f"backup_{time_stamp}.db")

        shutil.copy(DB_PATH, backup_file)

    # ---------------- SETTINGS HELPERS ---------------- #
    def get_monthly_budget(self):
        cursor.execute("SELECT monthly_budget FROM settings WHERE id=1")
        budget = cursor.fetchone()[0]
        return budget if budget else 0

    def set_monthly_budget(self, value):
        cursor.execute("UPDATE settings SET monthly_budget=? WHERE id=1", (value,))
        conn.commit()

    # ---------------- UI SETUP ---------------- #
    def setup_ui(self):
        self.root.configure(bg=self.theme["BG"])

        # SIDEBAR
        self.sidebar = tk.Frame(self.root, bg=self.theme["SIDEBAR"], width=250)
        self.sidebar.pack(side="left", fill="y")

        # MAIN AREA
        self.main_area = tk.Frame(self.root, bg=self.theme["BG"])
        self.main_area.pack(side="right", fill="both", expand=True)

        # HEADER BAR
        self.header = tk.Frame(self.main_area, bg=self.theme["HEADER"], height=60,
                               highlightbackground=self.theme["BORDER"], highlightthickness=1)
        self.header.pack(fill="x")

        tk.Label(self.header, text="✨ PocketPlanner",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.theme["HEADER"], fg=self.theme["TEXT"]).pack(side="left", padx=20)

        self.global_search_var = tk.StringVar()
        search_entry = tk.Entry(self.header, textvariable=self.global_search_var,
                                font=("Segoe UI", 11), width=30,
                                bg=self.theme["CARD"], fg=self.theme["TEXT"],
                                relief="flat")
        search_entry.pack(side="left", padx=10, pady=12)

        tk.Button(self.header, text="🔍 Search",
                  command=self.global_search,
                  bg=self.theme["ACCENT2"], fg=self.theme["TEXT"],
                  relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=12, pady=6).pack(side="left", padx=10)

        tk.Button(self.header, text="🌙 Theme",
                  command=self.toggle_theme,
                  bg=self.theme["PURPLE"], fg="white",
                  relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=12, pady=6).pack(side="right", padx=20)

        # SIDEBAR LOGO
        tk.Label(self.sidebar, text="💰", font=("Segoe UI", 40, "bold"),
                 bg=self.theme["SIDEBAR"], fg=self.theme["TEXT"]).pack(pady=15)

        tk.Label(self.sidebar, text="PocketPlanner",
                 font=("Segoe UI", 18, "bold"),
                 bg=self.theme["SIDEBAR"], fg=self.theme["TEXT"]).pack()

        tk.Label(self.sidebar, text="Ultimate Finance Tracker ✨",
                 font=("Segoe UI", 9, "bold"),
                 bg=self.theme["SIDEBAR"], fg=self.theme["MUTED"]).pack(pady=5)

        # SIDEBAR BUTTONS
        self.btn_dashboard = self.make_sidebar_button("🏠 Dashboard", self.show_dashboard)
        self.btn_add = self.make_sidebar_button("➕ Add Transaction", self.show_add_page)
        self.btn_trans = self.make_sidebar_button("📜 Transactions", self.show_transactions_page)
        self.btn_reports = self.make_sidebar_button("📊 Reports", self.show_reports_page)
        self.btn_settings = self.make_sidebar_button("⚙ Settings", self.show_settings_page)

        tk.Label(self.sidebar, text="Made by shri vardhan 💖",
                 font=("Segoe UI", 10, "bold"),
                 bg=self.theme["SIDEBAR"], fg=self.theme["PURPLE"]).pack(side="bottom", pady=15)

        # CONTENT FRAME
        self.content_frame = tk.Frame(self.main_area, bg=self.theme["BG"])
        self.content_frame.pack(fill="both", expand=True)

    def make_sidebar_button(self, text, command):
        btn = tk.Button(
            self.sidebar,
            text=text,
            command=lambda: self.set_active(btn, command),
            font=("Segoe UI", 11, "bold"),
            bg=self.theme["SIDEBAR"],
            fg=self.theme["TEXT"],
            relief="flat",
            anchor="w",
            padx=20,
            pady=12
        )
        btn.pack(fill="x", pady=4, padx=10)

        def on_enter(e):
            if btn != self.active_btn:
                btn.config(bg=self.theme["HOVER"])

        def on_leave(e):
            if btn != self.active_btn:
                btn.config(bg=self.theme["SIDEBAR"])

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        return btn

    def set_active(self, btn, command):
        if self.active_btn:
            self.active_btn.config(bg=self.theme["SIDEBAR"], fg=self.theme["TEXT"])

        btn.config(bg=self.theme["ACCENT2"], fg=self.theme["TEXT"])
        self.active_btn = btn
        command()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # ---------------- THEME SWITCH ---------------- #
    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.theme = DARK_THEME if self.is_dark else LIGHT_THEME

        for widget in self.root.winfo_children():
            widget.destroy()

        self.setup_styles()
        self.setup_ui()

        self.active_btn = None
        self.show_dashboard()

    # ---------------- GLOBAL SEARCH ---------------- #
    def global_search(self):
        text = self.global_search_var.get().strip().lower()
        if text == "":
            messagebox.showinfo("Search", "Type something to search!")
            return

        cursor.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()

        matches = []
        for row in rows:
            rid, title, amount, ttype, category, date = row
            combined = f"{rid} {title} {amount} {ttype} {category} {date}".lower()
            if text in combined:
                matches.append(row)

        if not matches:
            messagebox.showinfo("No Results", "No matching transactions found.")
            return

        self.show_transactions_page()
        self.search_var.set(text)
        self.refresh_transactions_table()

    # ---------------- DATABASE HELPERS ---------------- #
    def fetch_summary(self):
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='Income'")
        income = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='Expense'")
        expense = cursor.fetchone()[0] or 0

        balance = income - expense
        return income, expense, balance

    def fetch_month_expense(self):
        current_month = datetime.now().strftime("%m-%Y")

        cursor.execute("SELECT amount, date FROM transactions WHERE type='Expense'")
        rows = cursor.fetchall()

        total = 0
        for amount, date_str in rows:
            trans_month = datetime.strptime(date_str, "%d-%m-%Y %H:%M").strftime("%m-%Y")
            if trans_month == current_month:
                total += amount

        return total

    def get_category_summary(self):
        cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='Expense' GROUP BY category")
        rows = cursor.fetchall()
        rows.sort(key=lambda x: x[1], reverse=True)
        return rows

    # ---------------- DASHBOARD ---------------- #
    def show_dashboard(self):
        self.clear_content()

        tk.Label(self.content_frame, text="Dashboard ✨",
                 font=("Segoe UI", 24, "bold"),
                 bg=self.theme["BG"], fg=self.theme["TEXT"]).pack(anchor="w", padx=25, pady=15)

        income, expense, balance = self.fetch_summary()

        cards_frame = tk.Frame(self.content_frame, bg=self.theme["BG"])
        cards_frame.pack(fill="x", padx=25)

        self.make_card(cards_frame, "💚 Total Income", self.format_money(income), self.theme["ACCENT"])
        self.make_card(cards_frame, "❤️ Total Expense", self.format_money(expense), self.theme["DANGER"])
        self.make_card(cards_frame, "💰 Balance", self.format_money(balance), self.theme["PURPLE"])

        # MONTHLY BUDGET
        budget = self.get_monthly_budget()
        month_exp = self.fetch_month_expense()

        percent = 0
        budget_card = tk.Frame(self.content_frame, bg=self.theme["CARD"],
                               highlightbackground=self.theme["BORDER"], highlightthickness=2)
        budget_card.pack(fill="x", padx=25, pady=15)

        tk.Label(budget_card, text="📅 Monthly Budget Usage",
                 font=("Segoe UI", 14, "bold"),
                 bg=self.theme["CARD"], fg=self.theme["TEXT"]).pack(anchor="w", padx=15, pady=10)

        if budget > 0:
            percent = (month_exp / budget) * 100
            percent = min(percent, 100)
            remaining = budget - month_exp

            info = f"Spent {self.format_money(month_exp)} / Budget {self.format_money(budget)} ({percent:.1f}%) | Remaining {self.format_money(remaining)}"
        else:
            info = "No budget set. Go to Settings and set Monthly Budget."

        tk.Label(budget_card, text=info,
                 font=("Segoe UI", 11, "bold"),
                 bg=self.theme["CARD"], fg=self.theme["MUTED"]).pack(anchor="w", padx=15)

        pb = ttk.Progressbar(budget_card, length=850)
        pb.pack(padx=15, pady=12)
        pb["value"] = percent

        if budget > 0 and month_exp > budget:
            messagebox.showwarning("⚠ Budget Exceeded!",
                                   f"You exceeded your monthly budget!\n\nBudget: {self.format_money(budget)}\nSpent: {self.format_money(month_exp)}")

        # CHARTS GRID
        charts_grid = tk.Frame(self.content_frame, bg=self.theme["BG"])
        charts_grid.pack(fill="both", expand=True, padx=25, pady=10)

        # LEFT CHART (BAR)
        bar_card = tk.Frame(charts_grid, bg=self.theme["CARD"],
                            highlightbackground=self.theme["BORDER"], highlightthickness=2)
        bar_card.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        tk.Label(bar_card, text="📊 Income vs Expense",
                 font=("Segoe UI", 13, "bold"),
                 bg=self.theme["CARD"], fg=self.theme["TEXT"]).pack(anchor="w", padx=15, pady=10)

        bar_container = tk.Frame(bar_card, bg=self.theme["CARD"])
        bar_container.pack(fill="both", expand=True)

        self.draw_income_expense_chart(bar_container, income, expense)

        # RIGHT CHART (PIE)
        pie_card = tk.Frame(charts_grid, bg=self.theme["CARD"],
                            highlightbackground=self.theme["BORDER"], highlightthickness=2)
        pie_card.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        tk.Label(pie_card, text="🥧 Expense Categories",
                 font=("Segoe UI", 13, "bold"),
                 bg=self.theme["CARD"], fg=self.theme["TEXT"]).pack(anchor="w", padx=15, pady=10)

        pie_container = tk.Frame(pie_card, bg=self.theme["CARD"])
        pie_container.pack(fill="both", expand=True)

        self.draw_dashboard_pie(pie_container)

        # CATEGORY SUMMARY
        summary_card = tk.Frame(self.content_frame, bg=self.theme["CARD"],
                                highlightbackground=self.theme["BORDER"], highlightthickness=2)
        summary_card.pack(fill="x", padx=25, pady=15)

        tk.Label(summary_card, text="📌 Top Spending Categories",
                 font=("Segoe UI", 13, "bold"),
                 bg=self.theme["CARD"], fg=self.theme["TEXT"]).pack(anchor="w", padx=15, pady=10)

        summary_data = self.get_category_summary()

        if not summary_data:
            tk.Label(summary_card, text="No Expense Data Found!",
                     font=("Segoe UI", 11, "bold"),
                     bg=self.theme["CARD"], fg=self.theme["MUTED"]).pack(anchor="w", padx=15, pady=10)
        else:
            for cat, amt in summary_data[:5]:
                tk.Label(summary_card, text=f"{cat}   ➜   {self.format_money(amt)}",
                         font=("Segoe UI", 11, "bold"),
                         bg=self.theme["CARD"], fg=self.theme["MUTED"]).pack(anchor="w", padx=20, pady=3)

    def make_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg=self.theme["CARD"],
                        highlightbackground=self.theme["BORDER"], highlightthickness=2)
        card.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        tk.Label(card, text=title,
                 font=("Segoe UI", 11, "bold"),
                 bg=self.theme["CARD"], fg=self.theme["MUTED"]).pack(anchor="w", padx=15, pady=8)

        tk.Label(card, text=value,
                 font=("Segoe UI", 20, "bold"),
                 bg=self.theme["CARD"], fg=color).pack(anchor="w", padx=15, pady=5)

    def draw_income_expense_chart(self, frame, income, expense):
        for widget in frame.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)

        ax.bar(["Income", "Expense"], [income, expense])
        ax.set_title("Income vs Expense")
        ax.set_ylabel("Amount")

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def draw_dashboard_pie(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

        cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='Expense' GROUP BY category")
        rows = cursor.fetchall()

        if not rows:
            tk.Label(frame, text="No Expense Data!",
                     font=("Segoe UI", 12, "bold"),
                     bg=self.theme["CARD"], fg=self.theme["MUTED"]).pack(pady=50)
            return

        labels = [r[0] for r in rows]
        values = [r[1] for r in rows]

        fig = Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)

        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title("Expense Pie Chart")

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---------------- ADD TRANSACTION ---------------- #
    def show_add_page(self):
        self.clear_content()

        tk.Label(self.content_frame, text="Add Transaction ➕",
                 font=("Segoe UI", 24, "bold"),
                 bg=self.theme["BG"], fg=self.theme["TEXT"]).pack(anchor="w", padx=25, pady=20)

        card = tk.Frame(self.content_frame, bg=self.theme["CARD"],
                        highlightbackground=self.theme["BORDER"], highlightthickness=2)
        card.pack(padx=25, pady=10, fill="x")

        tk.Label(card, text="Title",
                 bg=self.theme["CARD"], fg=self.theme["MUTED"],
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, padx=20, pady=15)

        self.title_entry = tk.Entry(card, width=32, font=("Segoe UI", 12))
        self.title_entry.grid(row=0, column=1, padx=10)

        tk.Label(card, text="Amount",
                 bg=self.theme["CARD"], fg=self.theme["MUTED"],
                 font=("Segoe UI", 11, "bold")).grid(row=1, column=0, padx=20, pady=15)

        self.amount_entry = tk.Entry(card, width=32, font=("Segoe UI", 12))
        self.amount_entry.grid(row=1, column=1, padx=10)

        tk.Label(card, text="Type",
                 bg=self.theme["CARD"], fg=self.theme["MUTED"],
                 font=("Segoe UI", 11, "bold")).grid(row=2, column=0, padx=20, pady=15)

        self.type_var = tk.StringVar(value="Expense")
        ttk.Combobox(card, textvariable=self.type_var,
                     values=["Income", "Expense"], width=29).grid(row=2, column=1, padx=10)

        tk.Label(card, text="Category",
                 bg=self.theme["CARD"], fg=self.theme["MUTED"],
                 font=("Segoe UI", 11, "bold")).grid(row=3, column=0, padx=20, pady=15)

        self.category_var = tk.StringVar(value="Other ✨")
        ttk.Combobox(card, textvariable=self.category_var,
                     values=categories_list, width=29).grid(row=3, column=1, padx=10)

        tk.Button(self.content_frame, text="✨ Save Transaction",
                  command=self.add_transaction,
                  bg=self.theme["ACCENT"], fg="white",
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=25, pady=12).pack(pady=25)

        self.title_entry.focus_set()

    def add_transaction(self):
        title = self.title_entry.get().strip()
        amount = self.amount_entry.get().strip()
        t_type = self.type_var.get()
        category = self.category_var.get()

        if title == "" or amount == "":
            messagebox.showerror("Error", "Please fill all fields!")
            return

        try:
            amount = float(amount)
        except:
            messagebox.showerror("Error", "Amount must be a number!")
            return

        date = datetime.now().strftime("%d-%m-%Y %H:%M")

        cursor.execute("""
            INSERT INTO transactions (title, amount, type, category, date)
            VALUES (?, ?, ?, ?, ?)
        """, (title, amount, t_type, category, date))

        conn.commit()
        messagebox.showinfo("Saved ✨", "Transaction Added Successfully!")

        # stay in add page
        self.title_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.type_var.set("Expense")
        self.category_var.set("Other ✨")
        self.title_entry.focus_set()

    # ---------------- TRANSACTIONS PAGE ---------------- #
    def show_transactions_page(self):
        self.clear_content()

        tk.Label(self.content_frame, text="Transactions 📜",
                 font=("Segoe UI", 24, "bold"),
                 bg=self.theme["BG"], fg=self.theme["TEXT"]).pack(anchor="w", padx=25, pady=15)

        top_bar = tk.Frame(self.content_frame, bg=self.theme["BG"])
        top_bar.pack(fill="x", padx=25, pady=10)

        tk.Label(top_bar, text="🔍 Search:",
                 bg=self.theme["BG"], fg=self.theme["TEXT"],
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        self.search_var = tk.StringVar()
        tk.Entry(top_bar, textvariable=self.search_var,
                 font=("Segoe UI", 11), width=25).pack(side="left", padx=10)

        tk.Label(top_bar, text="Filter:",
                 bg=self.theme["BG"], fg=self.theme["TEXT"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)

        self.filter_var = tk.StringVar(value="All")
        ttk.Combobox(top_bar, textvariable=self.filter_var,
                     values=["All", "Income", "Expense"], width=12).pack(side="left", padx=5)

        tk.Label(top_bar, text="Sort:",
                 bg=self.theme["BG"], fg=self.theme["TEXT"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)

        self.sort_var = tk.StringVar(value="Latest")
        ttk.Combobox(top_bar, textvariable=self.sort_var,
                     values=["Latest", "Oldest", "Highest", "Lowest"], width=12).pack(side="left", padx=5)

        tk.Button(top_bar, text="Apply",
                  command=self.refresh_transactions_table,
                  bg=self.theme["ACCENT2"], fg=self.theme["TEXT"],
                  relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=12, pady=6).pack(side="left", padx=12)

        table_card = tk.Frame(self.content_frame, bg=self.theme["CARD"],
                              highlightbackground=self.theme["BORDER"], highlightthickness=2)
        table_card.pack(fill="both", expand=True, padx=25, pady=10)

        columns = ("ID", "Title", "Amount", "Type", "Category", "Date")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", height=15)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=170)

        self.tree.column("ID", width=60)

        btn_frame = tk.Frame(self.content_frame, bg=self.theme["BG"])
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="✏️ Edit",
                  command=self.edit_transaction,
                  bg=self.theme["ACCENT2"], fg=self.theme["TEXT"],
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=22, pady=8).pack(side="left", padx=10)

        tk.Button(btn_frame, text="🗑 Delete",
                  command=self.delete_transaction,
                  bg=self.theme["DANGER"], fg="white",
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=22, pady=8).pack(side="left", padx=10)

        self.refresh_transactions_table()

    def refresh_transactions_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_text = self.search_var.get().lower().strip()
        filter_type = self.filter_var.get()
        sort_option = self.sort_var.get()

        cursor.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()

        filtered = []
        for row in rows:
            rid, title, amount, ttype, category, date = row
            combined = f"{title} {amount} {ttype} {category} {date}".lower()

            if search_text and search_text not in combined:
                continue

            if filter_type != "All" and ttype != filter_type:
                continue

            filtered.append(row)

        if sort_option == "Latest":
            filtered.sort(key=lambda x: x[0], reverse=True)
        elif sort_option == "Oldest":
            filtered.sort(key=lambda x: x[0])
        elif sort_option == "Highest":
            filtered.sort(key=lambda x: x[2], reverse=True)
        elif sort_option == "Lowest":
            filtered.sort(key=lambda x: x[2])

        for row in filtered:
            self.tree.insert("", tk.END, values=row)

    def delete_transaction(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a transaction first!")
            return

        trans_id = self.tree.item(selected[0])["values"][0]

        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this transaction?")
        if not confirm:
            return

        cursor.execute("DELETE FROM transactions WHERE id=?", (trans_id,))
        conn.commit()

        messagebox.showinfo("Deleted", "Transaction deleted successfully!")
        self.refresh_transactions_table()

    def edit_transaction(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a transaction first!")
            return

        data = self.tree.item(selected[0])["values"]
        trans_id, title, amount, t_type, category, date = data

        win = tk.Toplevel(self.root)
        win.title("Edit Transaction ✏️")
        win.geometry("420x380")
        win.configure(bg=self.theme["BG"])
        win.resizable(False, False)

        tk.Label(win, text="Edit Transaction ✏️",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.theme["BG"], fg=self.theme["TEXT"]).pack(pady=12)

        title_entry = tk.Entry(win, width=30, font=("Segoe UI", 12))
        title_entry.pack(pady=10)
        title_entry.insert(0, title)

        amount_entry = tk.Entry(win, width=30, font=("Segoe UI", 12))
        amount_entry.pack(pady=10)
        amount_entry.insert(0, amount)

        type_var = tk.StringVar(value=t_type)
        ttk.Combobox(win, textvariable=type_var,
                     values=["Income", "Expense"], width=27).pack(pady=10)

        category_var = tk.StringVar(value=category)
        ttk.Combobox(win, textvariable=category_var,
                     values=categories_list, width=27).pack(pady=10)

        def save_edit():
            new_title = title_entry.get().strip()
            new_amount = amount_entry.get().strip()

            if new_title == "" or new_amount == "":
                messagebox.showerror("Error", "Fill all fields!")
                return

            try:
                new_amount = float(new_amount)
            except:
                messagebox.showerror("Error", "Amount must be number!")
                return

            cursor.execute("""
                UPDATE transactions
                SET title=?, amount=?, type=?, category=?
                WHERE id=?
            """, (new_title, new_amount, type_var.get(), category_var.get(), trans_id))

            conn.commit()
            messagebox.showinfo("Updated", "Transaction updated successfully!")
            win.destroy()
            self.refresh_transactions_table()

        tk.Button(win, text="💾 Save Changes",
                  command=save_edit,
                  bg=self.theme["ACCENT"], fg="white",
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=20)

    # ---------------- REPORTS PAGE ---------------- #
    def show_reports_page(self):
        self.clear_content()

        tk.Label(self.content_frame, text="Reports 📊",
                 font=("Segoe UI", 24, "bold"),
                 bg=self.theme["BG"], fg=self.theme["TEXT"]).pack(anchor="w", padx=25, pady=10)

        tk.Button(self.content_frame, text="📄 Download Monthly PDF Report",
                  command=self.export_monthly_pdf_report,
                  bg=self.theme["PURPLE"], fg="white",
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=5)

        tk.Button(self.content_frame, text="📄 Download Yearly PDF Report",
                  command=self.export_yearly_pdf_report,
                  bg=self.theme["PURPLE"], fg="white",
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=5)

        report_tabs = ttk.Notebook(self.content_frame)
        report_tabs.pack(fill="both", expand=True, padx=20, pady=10)

        monthly_tab = tk.Frame(report_tabs, bg=self.theme["BG"])
        report_tabs.add(monthly_tab, text="Monthly")

        yearly_tab = tk.Frame(report_tabs, bg=self.theme["BG"])
        report_tabs.add(yearly_tab, text="Yearly")

        pie_tab = tk.Frame(report_tabs, bg=self.theme["BG"])
        report_tabs.add(pie_tab, text="Category Pie")

        compare_tab = tk.Frame(report_tabs, bg=self.theme["BG"])
        report_tabs.add(compare_tab, text="3-Month Compare")

        # MONTHLY TAB
        self.month_var = tk.StringVar(value="All")

        top = tk.Frame(monthly_tab, bg=self.theme["BG"])
        top.pack(fill="x", padx=20, pady=15)

        tk.Label(top, text="Select Month:",
                 bg=self.theme["BG"], fg=self.theme["TEXT"],
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        months = ["All", "January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]

        ttk.Combobox(top, textvariable=self.month_var,
                     values=months, width=18).pack(side="left", padx=10)

        tk.Button(top, text="Show Report",
                  command=self.show_monthly_chart,
                  bg=self.theme["ACCENT2"], fg=self.theme["TEXT"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=12, pady=6).pack(side="left")

        self.month_chart_container = tk.Frame(monthly_tab, bg=self.theme["CARD"])
        self.month_chart_container.pack(fill="both", expand=True, padx=20, pady=20)

        # YEARLY TAB
        tk.Button(yearly_tab, text="📅 Show Yearly Expense Report",
                  command=self.show_yearly_chart,
                  bg=self.theme["ACCENT2"], fg=self.theme["TEXT"],
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=15, pady=8).pack(pady=15)

        self.year_chart_container = tk.Frame(yearly_tab, bg=self.theme["CARD"])
        self.year_chart_container.pack(fill="both", expand=True, padx=20, pady=20)

        # PIE TAB
        tk.Button(pie_tab, text="🥧 Show Category Pie Chart",
                  command=self.show_category_pie_chart,
                  bg=self.theme["ACCENT2"], fg=self.theme["TEXT"],
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=15, pady=8).pack(pady=15)

        self.pie_chart_container = tk.Frame(pie_tab, bg=self.theme["CARD"])
        self.pie_chart_container.pack(fill="both", expand=True, padx=20, pady=20)

        # COMPARE TAB
        tk.Label(compare_tab, text="📊 Last 3 Months Expense Comparison",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.theme["BG"], fg=self.theme["TEXT"]).pack(pady=15)

        self.compare_chart_container = tk.Frame(compare_tab, bg=self.theme["CARD"])
        self.compare_chart_container.pack(fill="both", expand=True, padx=20, pady=20)

        self.show_monthly_chart()
        self.show_3month_comparison_chart()

    def show_monthly_chart(self):
        for w in self.month_chart_container.winfo_children():
            w.destroy()

        month = self.month_var.get()

        cursor.execute("SELECT amount, type, date FROM transactions")
        rows = cursor.fetchall()

        income = 0
        expense = 0

        for amount, t_type, date_str in rows:
            trans_month = datetime.strptime(date_str, "%d-%m-%Y %H:%M").strftime("%B")

            if month == "All" or trans_month == month:
                if t_type == "Income":
                    income += amount
                else:
                    expense += amount

        fig = Figure(figsize=(7, 4), dpi=100)
        ax = fig.add_subplot(111)

        ax.bar(["Income", "Expense"], [income, expense])
        ax.set_title(f"{month} Report")
        ax.set_ylabel("Amount")

        canvas = FigureCanvasTkAgg(fig, master=self.month_chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def show_yearly_chart(self):
        for w in self.year_chart_container.winfo_children():
            w.destroy()

        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]

        month_expenses = {m: 0 for m in months}

        cursor.execute("SELECT amount, date FROM transactions WHERE type='Expense'")
        rows = cursor.fetchall()

        for amount, date_str in rows:
            m = datetime.strptime(date_str, "%d-%m-%Y %H:%M").strftime("%B")
            if m in month_expenses:
                month_expenses[m] += amount

        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)

        ax.bar(months, list(month_expenses.values()))
        ax.set_title("Yearly Expense Report")
        ax.set_ylabel("Expense")
        ax.tick_params(axis='x', rotation=45)

        canvas = FigureCanvasTkAgg(fig, master=self.year_chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def show_category_pie_chart(self):
        for w in self.pie_chart_container.winfo_children():
            w.destroy()

        cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='Expense' GROUP BY category")
        rows = cursor.fetchall()

        if not rows:
            tk.Label(self.pie_chart_container, text="No Expense Data Found!",
                     font=("Segoe UI", 14, "bold"),
                     bg=self.theme["CARD"], fg=self.theme["TEXT"]).pack(pady=50)
            return

        labels = [r[0] for r in rows]
        values = [r[1] for r in rows]

        fig = Figure(figsize=(6, 5), dpi=100)
        ax = fig.add_subplot(111)

        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title("Category Wise Expense")

        canvas = FigureCanvasTkAgg(fig, master=self.pie_chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def show_3month_comparison_chart(self):
        for w in self.compare_chart_container.winfo_children():
            w.destroy()

        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]

        current_index = datetime.now().month - 1

        selected_months = [
            months[(current_index - 2) % 12],
            months[(current_index - 1) % 12],
            months[current_index]
        ]

        month_expenses = {m: 0 for m in selected_months}

        cursor.execute("SELECT amount, date FROM transactions WHERE type='Expense'")
        rows = cursor.fetchall()

        for amount, date_str in rows:
            trans_month = datetime.strptime(date_str, "%d-%m-%Y %H:%M").strftime("%B")
            if trans_month in month_expenses:
                month_expenses[trans_month] += amount

        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)

        ax.bar(selected_months, list(month_expenses.values()))
        ax.set_title("Last 3 Months Expense Comparison")
        ax.set_ylabel("Expense Amount")

        canvas = FigureCanvasTkAgg(fig, master=self.compare_chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---------------- PDF MONTHLY REPORT ---------------- #
    def export_monthly_pdf_report(self):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
        except:
            messagebox.showerror("Missing Library", "Please install reportlab:\n\npip install reportlab")
            return

        month = datetime.now().strftime("%B")
        year = datetime.now().strftime("%Y")

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=f"PocketPlanner_Monthly_Report_{month}_{year}.pdf"
           
        )

        if not file_path:
            return

        cursor.execute("SELECT title, amount, type, category, date FROM transactions")
        rows = cursor.fetchall()

        total_income = 0
        total_expense = 0
        monthly_transactions = []
        category_totals = {}

        for title, amount, ttype, category, date_str in rows:
            trans_month = datetime.strptime(date_str, "%d-%m-%Y %H:%M").strftime("%B")
            trans_year = datetime.strptime(date_str, "%d-%m-%Y %H:%M").strftime("%Y")

            if trans_month == month and trans_year == year:
                monthly_transactions.append((title, amount, ttype, category, date_str))

                if ttype == "Income":
                    total_income += amount
                else:
                    total_expense += amount
                    category_totals[category] = category_totals.get(category, 0) + amount

        balance = total_income - total_expense
        budget = self.get_monthly_budget()

        # temp charts
        temp_dir = tempfile.gettempdir()
        bar_chart_path = os.path.join(temp_dir, "income_expense_chart.png")
        pie_chart_path = os.path.join(temp_dir, "category_pie_chart.png")

        fig1 = Figure(figsize=(5, 3), dpi=120)
        ax1 = fig1.add_subplot(111)
        ax1.bar(["Income", "Expense"], [total_income, total_expense])
        ax1.set_title("Income vs Expense")
        ax1.set_ylabel("Amount")
        fig1.savefig(bar_chart_path)

        if category_totals:
            labels = list(category_totals.keys())
            values = list(category_totals.values())

            fig2 = Figure(figsize=(5, 3), dpi=120)
            ax2 = fig2.add_subplot(111)
            ax2.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
            ax2.set_title("Expense Categories")
            fig2.savefig(pie_chart_path)

        # PDF
        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4
        y = height - 60

        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, y, "PocketPlanner Monthly Report")
        y -= 30

        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"Month: {month} {year}")
        y -= 20
        c.drawString(50, y, f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
        y -= 30

        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Summary")
        y -= 20

        c.setFont("Helvetica", 12)
        c.drawString(60, y, f"Total Income: {self.format_money(total_income)}")
        y -= 18
        c.drawString(60, y, f"Total Expense: {self.format_money(total_expense)}")
        y -= 18
        c.drawString(60, y, f"Balance: {self.format_money(balance)}")
        y -= 18
        c.drawString(60, y, f"Monthly Budget Set: {self.format_money(budget)}")
        y -= 25

        if budget > 0:
            percent = (total_expense / budget) * 100

            c.setFont("Helvetica-Bold", 12)
            if total_expense > budget:
                c.setFillColor(colors.red)
                c.drawString(60, y, f"⚠ Budget Exceeded ({percent:.1f}%)")
            else:
                c.setFillColor(colors.green)
                c.drawString(60, y, f"✅ Budget Safe ({percent:.1f}%)")

            c.setFillColor(colors.black)
            y -= 30

        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Charts")
        y -= 20

        if os.path.exists(bar_chart_path):
            c.drawImage(bar_chart_path, 60, y - 200, width=220, height=180)

        if os.path.exists(pie_chart_path):
            c.drawImage(pie_chart_path, 320, y - 200, width=220, height=180)

        y -= 240

        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Transactions List")
        y -= 25

        if not monthly_transactions:
            c.setFont("Helvetica", 12)
            c.drawString(60, y, "No transactions found for this month.")
            y -= 20
        else:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "Title")
            c.drawString(200, y, "Amount")
            c.drawString(290, y, "Type")
            c.drawString(350, y, "Category")
            c.drawString(470, y, "Date")
            y -= 15

            c.setFont("Helvetica", 9)

            for title, amount, ttype, category, date_str in monthly_transactions:
                if y < 80:
                    c.showPage()
                    y = height - 60

                c.drawString(50, y, title[:20])
                c.drawString(200, y, self.format_money(amount))
                c.drawString(290, y, ttype)
                c.drawString(350, y, category[:15])
                c.drawString(470, y, date_str)
                y -= 15

        c.setFont("Helvetica-Oblique", 10)
        c.drawString(50, 40, "Generated by PocketPlanner 💖")
        c.save()

        messagebox.showinfo("PDF Exported", f"Monthly report saved successfully!\n\n{file_path}")

    # ---------------- PDF YEARLY REPORT ---------------- #
    def export_yearly_pdf_report(self):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except:
            messagebox.showerror("Missing Library", "Please install reportlab:\n\npip install reportlab")
            return

        year = datetime.now().strftime("%Y")

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=f"PocketPlanner_Yearly_Report_{year}.pdf"
        )

        if not file_path:
            return

        cursor.execute("SELECT amount, type, date FROM transactions")
        rows = cursor.fetchall()

        total_income = 0
        total_expense = 0

        month_data = {
            "January": 0, "February": 0, "March": 0, "April": 0,
            "May": 0, "June": 0, "July": 0, "August": 0,
            "September": 0, "October": 0, "November": 0, "December": 0
        }

        for amount, ttype, date_str in rows:
            trans_year = datetime.strptime(date_str, "%d-%m-%Y %H:%M").strftime("%Y")
            trans_month = datetime.strptime(date_str, "%d-%m-%Y %H:%M").strftime("%B")

            if trans_year == year:
                if ttype == "Income":
                    total_income += amount
                else:
                    total_expense += amount
                    month_data[trans_month] += amount

        balance = total_income - total_expense

        temp_dir = tempfile.gettempdir()
        yearly_chart_path = os.path.join(temp_dir, "yearly_expense_chart.png")

        fig = Figure(figsize=(7, 3), dpi=120)
        ax = fig.add_subplot(111)

        months = list(month_data.keys())
        values = list(month_data.values())

        ax.bar(months, values)
        ax.set_title("Yearly Expense Chart")
        ax.set_ylabel("Expense")
        ax.tick_params(axis='x', rotation=45)

        fig.savefig(yearly_chart_path)

        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4
        y = height - 60

        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, y, "PocketPlanner Yearly Report")
        y -= 30

        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"Year: {year}")
        y -= 20
        c.drawString(50, y, f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
        y -= 30

        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Summary")
        y -= 20

        c.setFont("Helvetica", 12)
        c.drawString(60, y, f"Total Income: {self.format_money(total_income)}")
        y -= 18
        c.drawString(60, y, f"Total Expense: {self.format_money(total_expense)}")
        y -= 18
        c.drawString(60, y, f"Balance: {self.format_money(balance)}")
        y -= 30

        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Yearly Expense Chart")
        y -= 20

        if os.path.exists(yearly_chart_path):
            c.drawImage(yearly_chart_path, 70, y - 220, width=460, height=200)

        y -= 250

        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Month Wise Expense")
        y -= 20

        c.setFont("Helvetica", 11)
        for m, v in month_data.items():
            if y < 80:
                c.showPage()
                y = height - 60

            c.drawString(70, y, f"{m}: {self.format_money(v)}")
            y -= 15

        c.setFont("Helvetica-Oblique", 10)
        c.drawString(50, 40, "Generated by PocketPlanner 💖")

        c.save()

        messagebox.showinfo("PDF Exported", f"Yearly report saved successfully!\n\n{file_path}")

    # ---------------- SETTINGS PAGE ---------------- #
    def show_settings_page(self):
        self.clear_content()

        tk.Label(self.content_frame, text="Settings ⚙",
                 font=("Segoe UI", 24, "bold"),
                 bg=self.theme["BG"], fg=self.theme["TEXT"]).pack(anchor="w", padx=25, pady=20)

        # Currency Dropdown
        tk.Label(self.content_frame, text="Select Currency 💱",
                 bg=self.theme["BG"], fg=self.theme["TEXT"],
                 font=("Segoe UI", 12, "bold")).pack(pady=10)

        currency_var = tk.StringVar(value=self.get_currency())
        currency_list = ["INR", "USD", "EUR", "GBP", "JPY"]

        currency_box = ttk.Combobox(self.content_frame, textvariable=currency_var,
                                    values=currency_list, width=20)
        currency_box.pack(pady=5)

        def save_currency(event=None):
            self.set_currency(currency_var.get())
            messagebox.showinfo("Saved ✅", f"Currency set to {currency_var.get()}")
            self.show_dashboard()

        currency_box.bind("<<ComboboxSelected>>", save_currency)

        # Monthly Budget
        tk.Label(self.content_frame, text="Set Monthly Budget:",
                 bg=self.theme["BG"], fg=self.theme["TEXT"],
                 font=("Segoe UI", 12, "bold")).pack(pady=10)

        budget_entry = tk.Entry(self.content_frame, font=("Segoe UI", 12), width=20)
        budget_entry.pack(pady=5)
        budget_entry.insert(0, str(self.get_monthly_budget()))

        tk.Label(self.content_frame, text="💡 Press Enter to Save Budget",
                 bg=self.theme["BG"], fg=self.theme["MUTED"],
                 font=("Segoe UI", 10, "bold")).pack(pady=5)

        def save_budget(event=None):
            try:
                value = float(budget_entry.get())
                self.set_monthly_budget(value)
                messagebox.showinfo("Saved ✅", f"Monthly Budget set to {self.format_money(value)}")
                self.show_dashboard()
            except:
                messagebox.showerror("Error ❌", "Enter valid number!")

        budget_entry.bind("<Return>", save_budget)

        # Buttons
        tk.Button(self.content_frame, text="🔐 Change PIN",
                  command=self.change_pin_window,
                  bg=self.theme["ACCENT2"], fg=self.theme["TEXT"],
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=10)

        tk.Button(self.content_frame, text="❓ Change Security Question",
                  command=self.change_security_question,
                  bg=self.theme["ACCENT2"], fg=self.theme["TEXT"],
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=10)

        tk.Button(self.content_frame, text="📦 Backup Database",
                  command=self.backup_database,
                  bg=self.theme["PURPLE"], fg="white",
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=10)

        tk.Button(self.content_frame, text="♻ Restore Database",
                  command=self.restore_database,
                  bg=self.theme["PURPLE"], fg="white",
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=10)

        tk.Button(self.content_frame, text="⚠ Clear All Transactions",
                  command=self.clear_all_data,
                  bg=self.theme["DANGER"], fg="white",
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=10)

    # ---------------- CHANGE PIN ---------------- #
    def change_pin_window(self):
        win = tk.Toplevel(self.root)
        win.title("Change PIN 🔐")
        win.geometry("420x340")
        win.configure(bg=self.theme["BG"])
        win.resizable(False, False)

        tk.Label(win, text="Change PIN 🔐",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.theme["BG"], fg=self.theme["TEXT"]).pack(pady=15)

        tk.Label(win, text="Old PIN", bg=self.theme["BG"], fg=self.theme["MUTED"]).pack()
        old_entry = tk.Entry(win, show="*", font=("Segoe UI", 12))
        old_entry.pack(pady=5)

        tk.Label(win, text="New PIN", bg=self.theme["BG"], fg=self.theme["MUTED"]).pack()
        new_entry = tk.Entry(win, show="*", font=("Segoe UI", 12))
        new_entry.pack(pady=5)

        tk.Label(win, text="Confirm PIN", bg=self.theme["BG"], fg=self.theme["MUTED"]).pack()
        confirm_entry = tk.Entry(win, show="*", font=("Segoe UI", 12))
        confirm_entry.pack(pady=5)

        def save_new_pin():
            old_pin = old_entry.get()
            new_pin = new_entry.get()
            confirm_pin = confirm_entry.get()

            cursor.execute("SELECT app_pin FROM settings WHERE id=1")
            saved = cursor.fetchone()[0]

            if old_pin != saved:
                messagebox.showerror("Error", "Old PIN is wrong!")
                return

            if len(new_pin) < 4:
                messagebox.showerror("Error", "PIN must be at least 4 digits!")
                return

            if new_pin != confirm_pin:
                messagebox.showerror("Error", "PIN does not match!")
                return

            cursor.execute("UPDATE settings SET app_pin=? WHERE id=1", (new_pin,))
            conn.commit()

            messagebox.showinfo("Success", "PIN changed successfully!")
            win.destroy()

        tk.Button(win, text="💾 Save PIN",
                  command=save_new_pin,
                  bg=self.theme["ACCENT"], fg="white",
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=15)

    # ---------------- CHANGE SECURITY QUESTION ---------------- #
    def change_security_question(self):
        win = tk.Toplevel(self.root)
        win.title("Security Question ❓")
        win.geometry("460x340")
        win.configure(bg=self.theme["BG"])
        win.resizable(False, False)

        tk.Label(win, text="Change Security Question ❓",
                 font=("Segoe UI", 15, "bold"),
                 bg=self.theme["BG"], fg=self.theme["TEXT"]).pack(pady=15)

        tk.Label(win, text="New Question", bg=self.theme["BG"], fg=self.theme["MUTED"]).pack()
        q_entry = tk.Entry(win, font=("Segoe UI", 12), width=35)
        q_entry.pack(pady=8)

        tk.Label(win, text="New Answer", bg=self.theme["BG"], fg=self.theme["MUTED"]).pack()
        a_entry = tk.Entry(win, font=("Segoe UI", 12), width=35)
        a_entry.pack(pady=8)

        def save_security():
            q = q_entry.get().strip()
            a = a_entry.get().strip()

            if q == "" or a == "":
                messagebox.showerror("Error", "Fill all fields!")
                return

            cursor.execute("UPDATE settings SET security_question=?, security_answer=? WHERE id=1", (q, a))
            conn.commit()

            messagebox.showinfo("Saved", "Security Question Updated!")
            win.destroy()

        tk.Button(win, text="💾 Save",
                  command=save_security,
                  bg=self.theme["ACCENT"], fg="white",
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=20, pady=10).pack(pady=20)

    # ---------------- CLEAR ALL DATA ---------------- #
    def clear_all_data(self):
        confirm = messagebox.askyesno("Confirm", "Delete ALL transactions?")
        if confirm:
            cursor.execute("DELETE FROM transactions")
            conn.commit()
            messagebox.showinfo("Done", "All transactions deleted!")
            self.show_dashboard()

    # ---------------- BACKUP / RESTORE ---------------- #
    def backup_database(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".db",
                                                 filetypes=[("Database Files", "*.db")])
        if not file_path:
            return

        shutil.copy(DB_PATH, file_path)
        messagebox.showinfo("Backup", "Database backup saved successfully!")

    def restore_database(self):
        file_path = filedialog.askopenfilename(filetypes=[("Database Files", "*.db")])
        if not file_path:
            return

        confirm = messagebox.askyesno("Restore", "Restoring will overwrite current data. Continue?")
        if not confirm:
            return

        try:
            conn.close()
        except:
            pass

        shutil.copy(file_path, DB_PATH)

        messagebox.showinfo("Restore", "Database restored successfully!\n\nRestart app now.")
        self.root.destroy()


# ==========================================================
# SPLASH SCREEN
# ==========================================================
def splash_screen():
    splash = tk.Tk()
    splash.title("Loading...")
    splash.geometry("460x260")
    splash.configure(bg="#121212")
    splash.resizable(False, False)



    label = tk.Label(splash, text="💰 PocketPlanner",
                     font=("Segoe UI", 30, "bold"),
                     bg="#121212", fg="white")
    label.pack(pady=40)

    loading = tk.Label(splash, text="Loading",
                       font=("Segoe UI", 14, "bold"),
                       bg="#121212", fg="gray")
    loading.pack()

    dots = ["", ".", "..", "..."]
    i = 0

    def animate():
        nonlocal i
        loading.config(text="Loading" + dots[i % 4] + " ✨")
        i += 1
        splash.after(400, animate)

    animate()
    splash.after(2300, splash.destroy)
    splash.mainloop()


# ==========================================================
# LOGIN SCREEN WITH FORGOT PIN
# ==========================================================
def open_login():
    login = tk.Tk()
    login.title("PocketPlanner Login 🔐")
    login.geometry("430x470")
    login.configure(bg="#121212")
    login.resizable(False, False)



    entered_pin = tk.StringVar()

    tk.Label(login, text="🔐 PocketPlanner Login",
             font=("Segoe UI", 20, "bold"),
             bg="#121212", fg="white").pack(pady=30)

    tk.Label(login, text="Enter PIN",
             font=("Segoe UI", 11, "bold"),
             bg="#121212", fg="gray").pack(pady=5)

    pin_display = tk.Entry(login, textvariable=entered_pin,
                           font=("Segoe UI", 18),
                           show="*", justify="center", width=12)
    pin_display.pack(pady=20)
    pin_display.focus_set()

    def check_pin(event=None):
        cursor.execute("SELECT app_pin FROM settings WHERE id=1")
        saved_pin = cursor.fetchone()[0]

        if entered_pin.get() == saved_pin:
            login.destroy()
            open_main_app()
        else:
            messagebox.showerror("Wrong PIN", "Incorrect PIN!")
            entered_pin.set("")

    def forgot_pin():
        win = tk.Toplevel(login)
        win.title("Forgot PIN ❓")
        win.geometry("420x320")
        win.configure(bg="#121212")
        win.resizable(False, False)

        cursor.execute("SELECT security_question FROM settings WHERE id=1")
        question = cursor.fetchone()[0]

        tk.Label(win, text="Forgot PIN ❓",
                 font=("Segoe UI", 16, "bold"),
                 bg="#121212", fg="white").pack(pady=15)

        tk.Label(win, text=question,
                 font=("Segoe UI", 11),
                 bg="#121212", fg="gray").pack(pady=10)

        ans_entry = tk.Entry(win, font=("Segoe UI", 12), width=25)
        ans_entry.pack(pady=10)
        ans_entry.focus_set()

        def verify():
            answer = ans_entry.get().strip().lower()
            cursor.execute("SELECT security_answer FROM settings WHERE id=1")
            saved_ans = cursor.fetchone()[0].strip().lower()

            if answer == saved_ans:
                cursor.execute("UPDATE settings SET app_pin=? WHERE id=1", ("1234",))
                conn.commit()
                messagebox.showinfo("Reset Success", "PIN reset to: 1234")
                win.destroy()
            else:
                messagebox.showerror("Wrong Answer", "Incorrect Answer!")

        tk.Button(win, text="Verify",
                  command=verify,
                  bg="#6BCB77", fg="black",
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=15, pady=8).pack(pady=15)

    rb = rounded_button(login, "Login", check_pin, "#6BCB77", "black")
    rb.pack(pady=15)

    tk.Button(login, text="Forgot PIN?",
              command=forgot_pin,
              bg="#121212", fg="gray",
              font=("Segoe UI", 10, "bold"),
              relief="flat").pack(pady=10)

    login.bind("<Return>", check_pin)
    login.mainloop()


def open_main_app():
    root = tk.Tk()
    BudgetApp(root)
    root.mainloop()


# ==========================================================
# RUN APP
# ==========================================================
if __name__ == "__main__":
    splash_screen()
    open_login()
