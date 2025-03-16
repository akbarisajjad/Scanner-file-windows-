import os
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import csv
from PIL import Image, UnidentifiedImageError
from mutagen import File as AudioFile
import ffmpeg
from PyPDF2 import PdfReader
from tqdm import tqdm
import threading
import zipfile
import rarfile
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- تابع محاسبه هش فایل ----------
def get_file_hash(file_path):
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as file:
            while chunk := file.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        print(f"فایل یافت نشد: {file_path}")
    except Exception as e:
        print(f"خطا در محاسبه هش فایل {file_path}: {e}")
    return None

# ---------- تابع بررسی سلامت فایل ----------
def check_file_integrity(file_path):
    try:
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            Image.open(file_path).verify()
        elif file_path.lower().endswith(('.mp3', '.wav', '.ogg')):
            AudioFile(file_path)
        elif file_path.lower().endswith(('.mp4', '.avi', '.mkv')):
            ffmpeg.probe(file_path)
        elif file_path.lower().endswith('.pdf'):
            PdfReader(file_path)
        elif file_path.lower().endswith(('.txt', '.log', '.csv')):
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read()
        elif file_path.lower().endswith(('.zip', '.rar')):
            if file_path.lower().endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.testzip()
            elif file_path.lower().endswith('.rar'):
                with rarfile.RarFile(file_path, 'r') as rar_ref:
                    rar_ref.testrar()
        return "سالم"
    except (UnidentifiedImageError, ffmpeg.Error, rarfile.Error, zipfile.BadZipFile):
        return "خراب"
    except Exception as e:
        print(f"خطا در بررسی سلامت فایل {file_path}: {e}")
        return "خراب"

# ---------- تابع اسکن فایل‌ها ----------
def scan_files(directory):
    file_hashes = {}
    duplicates = []
    report = []

    def process_file(file_path):
        hash_value = get_file_hash(file_path)
        status = check_file_integrity(file_path)

        if hash_value:
            if hash_value in file_hashes:
                duplicates.append(file_path)
            else:
                file_hashes[hash_value] = file_path

        report.append({
            "file_name": os.path.basename(file_path),
            "path": file_path,
            "status": status,
            "size_kb": round(os.path.getsize(file_path) / 1024, 2)
        })

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                futures.append(executor.submit(process_file, file_path))

        for future in tqdm(as_completed(futures), total=len(futures), desc="در حال بررسی فایل‌ها"):
            future.result()

    return report, duplicates

# ---------- تابع ذخیره گزارش ----------
def save_report(report, duplicates):
    try:
        with open('report.json', 'w', encoding='utf-8') as json_file:
            json.dump(report, json_file, ensure_ascii=False, indent=4)

        with open('report.csv', 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=["file_name", "path", "status", "size_kb"])
            writer.writeheader()
            writer.writerows(report)
    except Exception as e:
        print(f"خطا در ذخیره گزارش: {e}")

# ---------- حذف فایل‌های تکراری ----------
def delete_duplicates(duplicates):
    for file_path in duplicates:
        try:
            os.remove(file_path)
            print(f"فایل تکراری حذف شد: {file_path}")
        except Exception as e:
            print(f"خطا در حذف فایل {file_path}: {e}")

# ---------- رویداد شروع اسکن ----------
def start_scan():
    directory = filedialog.askdirectory()
    if directory:
        def scan():
            report, duplicates = scan_files(directory)
            save_report(report, duplicates)

            if duplicates:
                confirm = messagebox.askyesno("حذف فایل‌های تکراری", "فایل‌های تکراری شناسایی شدند. آیا می‌خواهید آن‌ها را حذف کنید؟")
                if confirm:
                    delete_duplicates(duplicates)
                    messagebox.showinfo("حذف موفق", "فایل‌های تکراری حذف شدند.")
            
            messagebox.showinfo("گزارش‌گیری کامل", "اسکن به پایان رسید. گزارش‌ها در فایل‌های report.json و report.csv ذخیره شدند.")
            scan_button.config(state=tk.NORMAL)

        scan_button.config(state=tk.DISABLED)
        threading.Thread(target=scan).start()

# ---------- ساخت رابط کاربری ----------
root = tk.Tk()
root.title("بررسی فایل‌های تکراری و خراب")
root.geometry("400x200")

frame = ttk.Frame(root, padding=20)
frame.pack()

ttk.Label(frame, text="بررسی فایل‌های تکراری و خراب").pack(pady=10)
scan_button = ttk.Button(frame, text="شروع اسکن", command=start_scan)
scan_button.pack(pady=10)
ttk.Button(frame, text="خروج", command=root.quit).pack(pady=10)

root.mainloop()
