import tkinter as tk
from tkinter import messagebox
from pymongo import MongoClient
from cryptography.fernet import Fernet
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import string
import random
import os
import shutil
import subprocess

# ================= DATABASE =================
client = MongoClient("mongodb://localhost:27017/")
db = client["password_manager"]
collection = db["passwords"]

def insert_data(website, username, encrypted):
    collection.insert_one({
        "website": website.lower(), # Store as lowercase for easier searching
        "username": username,
        "password": encrypted
    })

def fetch_data(website=None):
    if website:
        # Search for a specific website (case-insensitive)
        return list(collection.find({"website": website.lower()}))
    return list(collection.find())

def delete_data(website):
    return collection.delete_one({"website": website.lower()})

# ================= ENCRYPTION =================
KEY_FILE = "key.key"

def load_or_generate_key():
    if os.path.exists(KEY_FILE):
        return open(KEY_FILE, "rb").read()
    else:
        new_key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(new_key)
        return new_key

key = load_or_generate_key()
cipher = Fernet(key)

def encrypt_password(password):
    return cipher.encrypt(password.encode())

def decrypt_password(encrypted):
    try:
        return cipher.decrypt(encrypted).decode()
    except Exception:
        return "DECRYPTION_ERROR"

def generate_password():
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(chars) for _ in range(12))
    password_entry.delete(0, tk.END)
    password_entry.insert(0, password)

# ================= ANALYSIS =================
def check_strength(password):
    if password == "DECRYPTION_ERROR": return 0
    score = 0
    if len(password) >= 8: score += 1
    if any(c.isdigit() for c in password): score += 1
    if any(c.isupper() for c in password): score += 1
    if any(c in string.punctuation for c in password): score += 1
    return score

def show_graph():
    records = fetch_data()
    if not records:
        messagebox.showinfo("Info", "No data found for analysis")
        return

    strengths = []
    for r in records:
        pwd = decrypt_password(r["password"])
        strengths.append(check_strength(pwd))

    strengths = np.array(strengths)
    weak = np.sum(strengths <= 2)
    strong = np.sum(strengths > 2)

    plt.bar(["Weak", "Strong"], [weak, strong], color=['red', 'green'])
    plt.title("Password Strength Analysis")
    plt.show()

# ================= SEARCH & VIEW FUNCTIONS =================
def view_individual_password():
    # Automatically get website name from the entry field
    website_query = website_entry.get().strip()
    
    if not website_query:
        messagebox.showerror("Error", "Please enter a Website name to search")
        return

    records = fetch_data(website=website_query)
    
    if not records:
        messagebox.showinfo("Not Found", f"No saved password for '{website_query}'")
        return

    # Process records found
    data = []
    for r in records:
        decrypted = decrypt_password(r["password"])
        data.append({
            "Website": r["website"],
            "Username": r["username"],
            "Password": decrypted
        })

    df = pd.DataFrame(data)
    
    # Create a small popup for the result
    window = tk.Toplevel(root)
    window.title(f"Search Results: {website_query}")
    window.geometry("350x150")
    
    text = tk.Text(window, font=("Courier", 10), height=5)
    text.pack(padx=10, pady=10)
    text.insert("1.0", df.to_string(index=False))

def add_password():
    website = website_entry.get().strip()
    username = username_entry.get().strip()
    password = password_entry.get().strip()

    if not website or not username or not password:
        messagebox.showerror("Error", "All fields required")
        return

    encrypted = encrypt_password(password)
    insert_data(website, username, encrypted)
    messagebox.showinfo("Success", f"Credentials for {website} saved!")
    
    website_entry.delete(0, tk.END)
    username_entry.delete(0, tk.END)
    password_entry.delete(0, tk.END)

def delete_password():
    website = website_entry.get().strip()
    if not website:
        messagebox.showerror("Error", "Enter website name to delete")
        return

    result = delete_data(website)
    if result.deleted_count > 0:
        messagebox.showinfo("Success", f"Deleted {website}")
        website_entry.delete(0, tk.END)
    else:
        messagebox.showerror("Error", "Record not found")

# ================= GUI DISPLAY SETUP =================
def ensure_display():
    if os.environ.get("DISPLAY"):
        return

    xvfb = shutil.which("Xvfb")
    if not xvfb:
        raise RuntimeError("No display is available and Xvfb is not installed. Install xvfb to run this app in a headless environment.")

    display_num = ":99"
    subprocess.Popen(
        [xvfb, display_num, "-screen", "0", "1024x768x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )
    os.environ["DISPLAY"] = display_num

# ================= GUI SETUP =================
def setup_gui():
    global root, website_entry, username_entry, password_entry

    root = tk.Tk()
    root.title("SecurePass Manager")
    root.geometry("450x280")

    # Row 0: Website + Search Button
    tk.Label(root, text="Website").grid(row=0, column=0, pady=5, padx=5)
    website_entry = tk.Entry(root)
    website_entry.grid(row=0, column=1, pady=5)
    tk.Button(root, text="Search/View", command=view_individual_password, bg="lightblue").grid(row=0, column=2, padx=5)

    # Row 1: Username
    tk.Label(root, text="Username").grid(row=1, column=0, pady=5, padx=5)
    username_entry = tk.Entry(root)
    username_entry.grid(row=1, column=1, pady=5)

    # Row 2: Password + Generate Button
    tk.Label(root, text="Password").grid(row=2, column=0, pady=5, padx=5)
    password_entry = tk.Entry(root)
    password_entry.grid(row=2, column=1, pady=5)
    tk.Button(root, text="Generate", command=generate_password).grid(row=2, column=2, padx=5)

    # Row 3: Action Buttons
    tk.Button(root, text="Add New", command=add_password, width=12).grid(row=3, column=0, pady=20)
    tk.Button(root, text="Delete Selected", command=delete_password, width=12).grid(row=3, column=2, pady=20)
    
    # Row 4: Analysis
    tk.Button(root, text="Show Strength Analysis (All Data)", command=show_graph).grid(row=4, column=0, columnspan=3, pady=5)

    return root

if __name__ == "__main__":
    ensure_display()
    root = setup_gui()
    root.mainloop()