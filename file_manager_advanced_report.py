import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from plyer import notification
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, UnidentifiedImageError
from mutagen import File as AudioFile
from PyPDF2 import PdfReader
import zipfile
import rarfile

# ---------- توابع کمکی ----------
def get_file_size_mb(file_path):
    return os.path.getsize(file_path) / (1024 * 1024)

def send_notification(message):
    notification.notify(
        title="گزارش پیشرفته نرم‌افزار مدیریت فایل",
        message=message,
        timeout=5
    )

def check_file_integrity(file_path):
    try:
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            Image.open(file_path).verify()
        elif file_path.lower().endswith(('.mp3', '.wav', '.ogg')):
            AudioFile(file_path)
        elif file_path.lower().endswith('.pdf'):
            PdfReader(file_path)
        elif file_path.lower().endswith(('.zip', '.rar')):
            if file_path.lower().endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.testzip()
            elif file_path.lower().endswith('.rar'):
                with rarfile.RarFile(file_path, 'r') as rar_ref:
                    rar_ref.testrar()
        return "سالم"
    except Exception:
        return "خراب"

def generate_report(directory):
    report_data = {
        "File Name": [],
        "Size (MB)": [],
        "Status": [],
    }

    total_files = 0
    junk_files = 0
    large_files = 0
    corrupted_files = 0

    junk_extensions = [".tmp", ".temp", ".log", ".bak", ".old"]

    def process_file(file_path):
        nonlocal total_files, junk_files, large_files, corrupted_files
        total_files += 1
        size_mb = get_file_size_mb(file_path)

        try:
            status = "Normal"
            if file_path.lower().endswith(tuple(junk_extensions)):
                status = "Junk"
                junk_files += 1
            elif size_mb >= 100:
                status = "Large"
                large_files += 1
            elif check_file_integrity(file_path) == "خراب":
                status = "Corrupted"
                corrupted_files += 1
        except Exception:
            status = "Corrupted"
            corrupted_files += 1

        report_data["File Name"].append(os.path.basename(file_path))
        report_data["Size (MB)"].append(round(size_mb, 2))
        report_data["Status"].append(status)

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                futures.append(executor.submit(process_file, file_path))

        for future in as_completed(futures):
            future.result()

    df = pd.DataFrame(report_data)
    report_file = f"advanced_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    with PdfPages(report_file) as pdf:
        plt.figure(figsize=(6, 4))
        plt.bar(["Total", "Junk", "Large", "Corrupted"], [total_files, junk_files, large_files, corrupted_files], color=["blue", "orange", "green", "red"])
        plt.title("خلاصه وضعیت فایل‌ها")
        plt.xlabel("نوع فایل‌ها")
        plt.ylabel("تعداد")
        pdf.savefig()
        plt.close()

        plt.figure(figsize=(8, 4))
        plt.axis('tight')
        plt.axis('off')
        table = plt.table(cellText=df.values, colLabels=df.columns, loc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.auto_set_column_width(col=list(range(len(df.columns))))
        pdf.savefig()
        plt.close()

    send_notification(f"گزارش پیشرفته تولید شد: {report_file}")
    messagebox.showinfo("گزارش‌گیری موفق", f"گزارش پیشرفته با موفقیت ذخیره شد: {report_file}")

# ---------- رابط کاربری ----------
def select_directory():
    directory = filedialog.askdirectory(title="انتخاب پوشه برای گزارش‌گیری پیشرفته")
    if directory:
        generate_report(directory)

root = tk.Tk()
root.title("گزارش‌گیری پیشرفته مدیریت فایل‌ها")
root.geometry("600x400")

frame = ttk.Frame(root, padding=20)
frame.pack(fill="both", expand=True)

ttk.Label(frame, text="گزارش‌گیری پیشرفته با نمودارها", font=("Arial", 16, "bold")).pack(pady=10)

ttk.Button(frame, text="انتخاب پوشه و تولید گزارش", command=select_directory).pack(pady=20)

root.mainloop()
