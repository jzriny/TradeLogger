import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import datetime

# ---------------- Database Setup ---------------- #
conn = sqlite3.connect("trading_journal.db")
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY,
    date TEXT,
    time TEXT,
    instrument TEXT,
    session TEXT,
    account_size REAL,
    setup_name TEXT,
    entry_price REAL,
    exit_price REAL,
    stop_loss REAL,
    position_size REAL,
    direction TEXT,
    pnl_net REAL,
    commission REAL,
    context TEXT,
    bias TEXT,
    duration TEXT,
    mental_state_pre TEXT,
    mental_state_during TEXT,
    execution_quality TEXT,
    distractions TEXT
)''')
conn.commit()

# ---------------- Global Settings ---------------- #
settings = {
    "commission_per_contract": 0.35,  # default
    "text_size": 12,
    "dark_mode": False,
    "screenshot_folder": ""
}

# ---------------- Helper Functions ---------------- #
def calculate_pnl(entry, exit, size, direction, commission, multiplier=1.0):
    """Calculate Net P&L for long/short positions"""
    if direction.lower() == "long":
        gross = (exit - entry) * size * multiplier
    else:
        gross = (entry - exit) * size * multiplier
    net = gross - (commission * size)
    return net

# ---------------- Main Application ---------------- #
class TradingJournalApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Trading Journal & Profit Calculator")
        self.geometry("950x650")

        self.style = ttk.Style(self)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=1, fill="both")

        self.create_trade_tracker_tab()
        self.create_trade_history_tab()
        self.create_profit_calculator_tab()
        self.create_contract_specs_tab()
        self.create_settings_tab()

    # ---------------- Trade Tracker Tab ---------------- #
    def create_trade_tracker_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Trade Tracker")

        fields = [
            "Date", "Time", "Instrument", "Session", "Account Size", "Setup Name",
            "Entry Price", "Exit Price", "Stop Loss", "Position Size",
            "Direction (Long/Short)", "Context", "Bias", "Duration",
            "Mental State Pre", "Mental State During", "Execution Quality", "Distractions"
        ]
        self.trade_entries = {}

        for i, field in enumerate(fields):
            ttk.Label(tab, text=field).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            entry = ttk.Entry(tab)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.trade_entries[field] = entry

        def save_trade():
            data = {f: self.trade_entries[f].get() for f in fields}
            entry = float(data["Entry Price"])
            exit = float(data["Exit Price"])
            size = float(data["Position Size"])
            direction = data["Direction (Long/Short)"]
            commission = settings["commission_per_contract"]

            pnl_net = calculate_pnl(entry, exit, size, direction, commission)
            cursor.execute('''INSERT INTO trades 
                (date, time, instrument, session, account_size, setup_name,
                entry_price, exit_price, stop_loss, position_size, direction,
                pnl_net, commission, context, bias, duration,
                mental_state_pre, mental_state_during, execution_quality, distractions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (data["Date"], data["Time"], data["Instrument"], data["Session"], data["Account Size"], data["Setup Name"],
                 entry, exit, data["Stop Loss"], size, direction, pnl_net, commission,
                 data["Context"], data["Bias"], data["Duration"],
                 data["Mental State Pre"], data["Mental State During"], data["Execution Quality"], data["Distractions"]))
            conn.commit()
            messagebox.showinfo("Saved", f"Trade saved. Net P&L: {pnl_net:.2f}")

        ttk.Button(tab, text="Save Trade", command=save_trade).grid(row=len(fields), column=0, columnspan=2, pady=10)

    # ---------------- Trade History Tab ---------------- #
    def create_trade_history_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Trade History")

        self.history_tree = ttk.Treeview(tab, columns=("Date", "Instrument", "P&L", "Commission"), show="headings")
        for col in ("Date", "Instrument", "P&L", "Commission"):
            self.history_tree.heading(col, text=col)
        self.history_tree.pack(expand=1, fill="both")

        def load_history():
            for row in self.history_tree.get_children():
                self.history_tree.delete(row)
            cursor.execute("SELECT id, date, instrument, pnl_net, commission FROM trades ORDER BY id DESC")
            for row in cursor.fetchall():
                self.history_tree.insert("", "end", iid=row[0], values=row[1:])

        def delete_trade():
            selected = self.history_tree.selection()
            if not selected:
                return
            trade_id = selected[0]
            cursor.execute("DELETE FROM trades WHERE id=?", (trade_id,))
            conn.commit()
            load_history()

        ttk.Button(tab, text="Refresh", command=load_history).pack(side="left", padx=5, pady=5)
        ttk.Button(tab, text="Delete Selected", command=delete_trade).pack(side="left", padx=5, pady=5)

        load_history()

    # ---------------- Profit Calculator Tab ---------------- #
    def create_profit_calculator_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Profit Calculator")

        self.calc_frame = ttk.Frame(tab)
        self.calc_frame.pack(pady=10)

        ttk.Label(tab, text="Instrument Type:").pack(pady=5)
        self.instrument_type = ttk.Combobox(tab, values=["Stocks", "Forex", "Futures"])
        self.instrument_type.pack()
        self.instrument_type.bind("<<ComboboxSelected>>", self.update_calc_fields)

        self.dynamic_fields_frame = ttk.Frame(tab)
        self.dynamic_fields_frame.pack(pady=10)

        self.result_label = ttk.Label(tab, text="", font=("Arial", 12, "bold"))
        self.result_label.pack(pady=10)

    def update_calc_fields(self, event=None):
        for widget in self.dynamic_fields_frame.winfo_children():
            widget.destroy()

        choice = self.instrument_type.get()
        self.calc_entries = {}

        if choice == "Stocks":
            fields = ["Position Size", "Entry Price", "Exit Price"]
        elif choice == "Forex":
            fields = ["Currency Pair", "Direction (Long/Short)", "Trade Size (lots)", "Entry Price", "Exit Price"]
        else:  # Futures
            fields = ["Instrument", "Direction (Long/Short)", "Contracts", "Entry Price", "Exit Price"]

        for i, field in enumerate(fields):
            ttk.Label(self.dynamic_fields_frame, text=field).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            entry = ttk.Entry(self.dynamic_fields_frame)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.calc_entries[field] = entry

        ttk.Button(self.dynamic_fields_frame, text="Calculate Profit", command=self.calculate_profit).grid(
            row=len(fields), column=0, columnspan=2, pady=10
        )

    def calculate_profit(self):
        choice = self.instrument_type.get()
        commission = settings["commission_per_contract"]

        try:
            if choice == "Stocks":
                size = float(self.calc_entries["Position Size"].get())
                entry = float(self.calc_entries["Entry Price"].get())
                exit = float(self.calc_entries["Exit Price"].get())
                pnl = calculate_pnl(entry, exit, size, "long", commission)

            elif choice == "Forex":
                direction = self.calc_entries["Direction (Long/Short)"].get()
                size = float(self.calc_entries["Trade Size (lots)"].get()) * 100000  # standard lot
                entry = float(self.calc_entries["Entry Price"].get())
                exit = float(self.calc_entries["Exit Price"].get())
                pnl = calculate_pnl(entry, exit, size, direction, commission, multiplier=0.0001)

            else:  # Futures
                instrument = self.calc_entries["Instrument"].get().upper()
                direction = self.calc_entries["Direction (Long/Short)"].get()
                size = float(self.calc_entries["Contracts"].get())
                entry = float(self.calc_entries["Entry Price"].get())
                exit = float(self.calc_entries["Exit Price"].get())

                multipliers = {"NQ1": 20, "ES1": 50, "PL1": 50, "CL1": 1000, "GC1": 100, "PA1": 100}
                multiplier = multipliers.get(instrument, 1)

                pnl = calculate_pnl(entry, exit, size, direction, commission, multiplier)

            self.result_label.config(text=f"Net P&L: {pnl:.2f} | Commission: {commission}")

        except Exception as e:
            self.result_label.config(text=f"Error: {e}")

    # ---------------- Contract Specs Tab ---------------- #
    def create_contract_specs_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Contract Specs")

        specs = {
            "CL1": "Crude Oil | Tick Size: 0.01 = $10 | Contract: 1,000 barrels",
            "ES1": "E-mini S&P 500 | Tick Size: 0.25 = $12.50 | Contract: $50 x Index",
            "GC1": "Gold | Tick Size: 0.10 = $10 | Contract: 100 troy ounces",
            "NQ1": "E-mini Nasdaq | Tick Size: 0.25 = $5 | Contract: $20 x Index",
            "PA1": "Palladium | Tick Size: 0.50 = $50 | Contract: 100 troy ounces",
            "PL1": "Platinum | Tick Size: 0.10 = $5 | Contract: 50 troy ounces",
        }

        for k, v in sorted(specs.items()):
            ttk.Label(tab, text=f"{k}: {v}").pack(anchor="w", padx=10, pady=3)

    # ---------------- Settings Tab ---------------- #
    def create_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")

        ttk.Label(tab, text="Commission per Contract:").pack(pady=5)
        commission_entry = ttk.Entry(tab)
        commission_entry.insert(0, settings["commission_per_contract"])
        commission_entry.pack()

        def save_settings():
            try:
                settings["commission_per_contract"] = float(commission_entry.get())
                messagebox.showinfo("Saved", "Settings updated successfully.")
            except:
                messagebox.showerror("Error", "Invalid commission value.")

        ttk.Button(tab, text="Save Settings", command=save_settings).pack(pady=10)


# ---------------- Run Application ---------------- #
if __name__ == "__main__":
    app = TradingJournalApp()
    app.mainloop()
