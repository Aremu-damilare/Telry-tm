import sqlite3
import pyperclip
import keyboard
import time

DB_NAME = 'clipboard_history.db'

# Initialize the database and create the table if it doesn't exist
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clipboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Save the new copied content, keeping only the last 2 entries
def save_to_db(content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO clipboard (content) VALUES (?)', (content,))
    conn.commit()

    # Keep only the last 2 items
    cursor.execute('SELECT COUNT(*) FROM clipboard')
    count = cursor.fetchone()[0]
    if count > 2:
        cursor.execute('DELETE FROM clipboard WHERE id = (SELECT MIN(id) FROM clipboard)')
        conn.commit()

    conn.close()

# Get the last two items from the database
def get_last_two_items():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM clipboard ORDER BY id DESC LIMIT 2')
    items = cursor.fetchall()
    conn.close()
    return [item[0] for item in items]

# Function to switch between the last and current copied items
def switch_clipboard():
    items = get_last_two_items()
    if len(items) == 2:
        current = pyperclip.paste()
        if current == items[0]:
            pyperclip.copy(items[1])
        else:
            pyperclip.copy(items[0])

# Function to monitor clipboard changes
def monitor_clipboard():
    last_copied = ''
    while True:
        # Check the clipboard content
        current = pyperclip.paste()
        if current != last_copied:
            last_copied = current
            save_to_db(current)
        
        time.sleep(0.5)  # Check every 0.5 seconds

# Setup global shortcuts
def setup_shortcuts():
    keyboard.add_hotkey('ctrl+shift+z', switch_clipboard)
    keyboard.add_hotkey('ctrl+shift+y', switch_clipboard)

# Main function
def main():
    init_db()
    setup_shortcuts()
    print("Clipboard manager is running... Press Ctrl+C to exit.")
    monitor_clipboard()

if __name__ == '__main__':
    main()
