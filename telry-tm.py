import sys
import sqlite3
import pyperclip
import keyboard
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QStackedWidget, QHBoxLayout, QFrame
)
import time
from PyQt5.QtWidgets import QScrollArea

# Database setup
DB_FILE = 'clipboard_history.db'


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key_name TEXT PRIMARY KEY,
            key_value TEXT NOT NULL
        )
    ''')
    
    # Create history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Ensure default hotkeys exist
    c.execute("INSERT OR IGNORE INTO settings (key_name, key_value) VALUES ('switch_key1', 'Ctrl+Shift+Z')")
    c.execute("INSERT OR IGNORE INTO settings (key_name, key_value) VALUES ('switch_key2', 'Ctrl+Shift+Y')")
    
    conn.commit()
    conn.close()


def store_clipboard(content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO history (content, timestamp) VALUES (?, CURRENT_TIMESTAMP)', (content,))
    conn.commit()

    # Keep only last 2 items
    c.execute('SELECT COUNT(*) FROM history')
    count = c.fetchone()[0]
    if count > 2:
        c.execute('''
            DELETE FROM history 
            WHERE id IN (
                SELECT id FROM history ORDER BY timestamp ASC LIMIT ?
            )
        ''', (count - 2,))
        conn.commit()

    conn.close()


def get_switch_keys():
    """Retrieve stored key combinations from the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key_value FROM settings WHERE key_name='switch_key1'")
    switch_key1 = c.fetchone()
    c.execute("SELECT key_value FROM settings WHERE key_name='switch_key2'")
    switch_key2 = c.fetchone()
    conn.close()
    return switch_key1[0] if switch_key1 else "Not Set", switch_key2[0] if switch_key2 else "Not Set"


def save_switch_key(key_name, key_value):
    """Save key combination to the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key_name, key_value) VALUES (?, ?)", (key_name, key_value))
    conn.commit()
    conn.close()


def get_last_two_items():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT content FROM history ORDER BY timestamp DESC LIMIT 2')
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows if row]  # Ensure only valid items are returned



# Clipboard Switch
def switch_clipboard():
    items = get_last_two_items()
    if len(items) == 2:
        items.reverse()
        pyperclip.copy(items[0])


class ClipboardApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telry-TM Beta")
        self.setGeometry(300, 300, 400, 300)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Restore window dragging functionality
        self.dragging = False
        self.offset = QPoint()

        # Load keys from DB
        self.switch_key1, self.switch_key2 = get_switch_keys()

        # Drop Shadow Effect
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 15px;
                border: 1px solid #e0e0e0;
            }
        """)

        # Start clipboard monitoring
        self.clipboard_monitor = ClipboardMonitor()
        self.clipboard_monitor.clipboard_changed.connect(self.show_history)
        self.clipboard_monitor.start()

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove extra margins
        self.setLayout(main_layout)

        # Custom Title Bar
        title_bar = QFrame()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: #f1f1f1; border-top-left-radius: 15px; border-top-right-radius: 15px;")
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 0, 10, 0)

        # Title Label
        title_label = QLabel("Telry-TM Beta")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))

        # Minimize and Close Buttons
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setFixedSize(30, 20)
        self.minimize_btn.setStyleSheet("background-color: #ddd; border-radius: 5px;")
        self.minimize_btn.clicked.connect(self.showMinimized)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(30, 20)
        self.close_btn.setStyleSheet("background-color: #f66; color: white; border-radius: 5px;")
        self.close_btn.clicked.connect(self.close)

        # Add Widgets to Title Bar
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.minimize_btn)
        title_layout.addWidget(self.close_btn)
        title_bar.setLayout(title_layout)
        main_layout.addWidget(title_bar)

        # Navigation Buttons
        nav_layout = QHBoxLayout()
        self.history_btn = QPushButton("History")
        self.history_btn.clicked.connect(self.show_history)
        nav_layout.addWidget(self.history_btn)

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        nav_layout.addWidget(self.settings_btn)

        main_layout.addLayout(nav_layout)

        # Stacked Widget for Pages
        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages)

      
        # History Page
        self.history_page = QWidget()
        history_layout = QVBoxLayout(self.history_page)

        self.history_label = QLabel("Clipboard History (Last 2):")
        self.history_label.setFont(QFont("Arial", 14, QFont.Bold))

        # Scroll Area for history content
        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_content = QLabel("")
        self.history_content.setWordWrap(True)
        self.history_content.setFixedWidth(350)  # Fixed width to prevent overflow
        self.history_content.setStyleSheet("border: 1px solid #ccc; padding: 5px;")  # Optional styling

        self.history_scroll.setWidget(self.history_content)

        history_layout.addWidget(self.history_label)
        history_layout.addWidget(self.history_scroll)

        self.show_history()

        self.pages.addWidget(self.history_page)

        # Settings Page
        self.settings_page = QWidget()
        settings_layout = QVBoxLayout(self.settings_page)

        # Switch Key 1
        self.switch_key1_label = QLabel(f"Switch Key 1: {self.switch_key1}")
        self.switch_key1_label.setFont(QFont("Arial", 10))
        self.switch_key1_button = QPushButton("Set Key 1")
        self.switch_key1_button.clicked.connect(lambda: self.capture_keys(1))
        settings_layout.addWidget(self.switch_key1_label)
        settings_layout.addWidget(self.switch_key1_button)

        # Switch Key 2
        self.switch_key2_label = QLabel(f"Switch Key 2: {self.switch_key2}")
        self.switch_key2_label.setFont(QFont("Arial", 10))
        self.switch_key2_button = QPushButton("Set Key 2")
        self.switch_key2_button.clicked.connect(lambda: self.capture_keys(2))
        settings_layout.addWidget(self.switch_key2_label)
        settings_layout.addWidget(self.switch_key2_button)

        # Save Button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        settings_layout.addWidget(self.save_button)

        self.save_status = QLabel("")
        settings_layout.addWidget(self.save_status)

        self.pages.addWidget(self.settings_page)

    def show_history(self):
        self.pages.setCurrentWidget(self.history_page)
        items = get_last_two_items()
        print("Retrieved History Items:", items)  # Debugging statement
        # history_text = "Clipboard History (Last 2):\n\n" + "\n".join(items)
        # self.history_label.setText(history_text)
        history_text = "\n\n".join(items) if items else "No history available."
        self.history_content.setText(history_text)
        self.history_page.update()  # Force UI update


    def show_settings(self):
        self.pages.setCurrentWidget(self.settings_page)

    def capture_keys(self, key_num):
        """Capture up to 3 keys and display them."""
        self.save_status.setText("Press up to 3 keys...")
        self.save_status.setStyleSheet("color: blue;")

        keys_pressed = []

        def on_press(event):
            if event.name not in keys_pressed:
                keys_pressed.append(event.name)
            if len(keys_pressed) >= 3:
                keyboard.unhook_all()
                key_combination = "+".join(keys_pressed)
                if key_num == 1:
                    self.switch_key1 = key_combination
                    self.switch_key1_label.setText(f"Switch Key 1: {key_combination}")
                else:
                    self.switch_key2 = key_combination
                    self.switch_key2_label.setText(f"Switch Key 2: {key_combination}")

                self.save_status.setText("Captured!")
                self.save_status.setStyleSheet("color: green;")

        keyboard.hook(on_press)

    def save_settings(self):
        """Save key combinations to database."""
        save_switch_key("switch_key1", self.switch_key1)
        save_switch_key("switch_key2", self.switch_key2)
        self.save_status.setText("Settings Saved!")
        self.save_status.setStyleSheet("color: green;")

    # Restore dragging functionality
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.dragging = False



# # Clipboard Monitoring
# def monitor_clipboard():
#     last_clipboard = pyperclip.paste()
#     while True:
#         current_clipboard = pyperclip.paste()
#         if current_clipboard != last_clipboard:
#             store_clipboard(current_clipboard)
#             last_clipboard = current_clipboard
#         time.sleep(1)


hotkeys = []
def setup_shortcuts():
    """Set up hotkeys dynamically from the database."""
    global hotkeys

    # Remove previous hotkeys
    for hk in hotkeys:
        try:
            keyboard.remove_hotkey(hk)
        except KeyError:
            pass  

    

    # Load keys from database
    switch_key1, switch_key2 = get_switch_keys()
    
    # Register new hotkeys
    hotkeys.append(keyboard.add_hotkey(switch_key1, switch_clipboard))
    hotkeys.append(keyboard.add_hotkey(switch_key2, switch_clipboard))

    print(f"Registered hotkeys: {switch_key1}, {switch_key2}")


from PyQt5.QtCore import QMetaObject, Qt, QThread, pyqtSignal

class ClipboardMonitor(QThread):
    clipboard_changed = pyqtSignal()

    def run(self):
        last_clipboard = pyperclip.paste()
        while True:
            current_clipboard = pyperclip.paste()
            if current_clipboard != last_clipboard:
                store_clipboard(current_clipboard)
                self.clipboard_changed.emit()  # Emit signal to update UI
                last_clipboard = current_clipboard
            time.sleep(1)  # Check every second



if __name__ == "__main__":
    init_db()
    setup_shortcuts()
    app = QApplication(sys.argv)
    window = ClipboardApp()
    window.show()
    sys.exit(app.exec_())






import os
import sys
import shutil
import winreg
import subprocess


exe_path = os.path.abspath(sys.argv[0])  # This gets the real exe path
APP_NAME = "telry-tm"
EXECUTABLE_NAME = exe_path

def add_to_startup():
    """Adds the program to Windows startup (if not already added)."""
    exe_path = os.path.abspath(sys.argv[0])  # Get the full path of the exe
    
    # Open Windows Registry and add the executable to startup
    key = winreg.HKEY_CURRENT_USER
    registry_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        with winreg.OpenKey(key, registry_path, 0, winreg.KEY_SET_VALUE) as reg_key:
            winreg.SetValueEx(reg_key, APP_NAME, 0, winreg.REG_SZ, exe_path)
    except FileNotFoundError:
        with winreg.CreateKey(key, registry_path) as reg_key:
            winreg.SetValueEx(reg_key, APP_NAME, 0, winreg.REG_SZ, exe_path)

    print(f"{APP_NAME} added to startup.")

def run_in_background():
    """Restarts the script in background and exits the current process."""
    if not getattr(sys, 'frozen', False):
        print("Running in console mode, no need to restart.")
        return
    
    # Run the program again in background mode (without console window)
    subprocess.Popen([sys.executable], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
    sys.exit()  # Close the current process

if __name__ == "__main__":
    add_to_startup()  # Step 1: Add the program to startup automatically

    # Check if the user closed the interface, then restart in background
    if len(sys.argv) > 1 and sys.argv[1] == "--background":
        print("Running in background mode...")
        while True:
            pass  # Your background logic goes here
    else:
        print("Starting the main program with interface...")
        # Your GUI or script logic here
        input("Press ENTER to close and run in background...")
        run_in_background()  # Step 2: Restart in background mode
