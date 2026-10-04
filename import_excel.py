import os
import openpyxl
import gspread
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "MonTracker")
EXCEL_FILE = "rekap money manager.xlsx"

print(f"📊 Membaca file '{EXCEL_FILE}'...")
wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
ws_excel = wb.active
excel_rows = list(ws_excel.iter_rows(values_only=True))

prepared_rows = []
for r in excel_rows[1:]:
    period = r[0]
    if hasattr(period, "strftime"):
        date_str = period.strftime("%Y-%m-%d")
    else:
        date_str = str(period)[:10]

    cat = r[2] if r[2] else "Other"
    note = r[4] if r[4] else (r[7] if r[7] else cat)
    type_ = r[6] if r[6] else "Exp."
    amount = int(round(float(r[8]))) if r[8] is not None else 0

    prepared_rows.append([date_str, str(note).strip(), str(cat).strip(), amount, str(type_).strip()])

# Balik urutan agar dari terlama ke terbaru (Desember 2025 -> Oktober 2026)
prepared_rows.reverse()
print(f"✅ Berhasil memproses {len(prepared_rows)} transaksi historis dari Excel.")

# Koneksi ke Google Sheets
print(f"🔌 Menghubungkan ke Google Sheets '{SPREADSHEET_NAME}'...")
gc = gspread.service_account(filename="credentials.json")
sh = gc.open(SPREADSHEET_NAME)
ws = sh.sheet1

# Ambil data yang sudah ada di Google Sheets saat ini
existing_data = ws.get_all_values()
print(f"📋 Ditemukan {len(existing_data)} baris data di Google Sheets saat ini.")

existing_rows_formatted = []
for row in existing_data:
    if not row or not any(row):
        continue
    # Lewati jika baris pertama kebetulan sudah berupa header
    if row[0].lower() in ["tanggal", "date", "period"]:
        continue
    # Format baris: Tanggal, Item, Kategori, Nominal, Tipe
    date_val = row[0]
    item_val = row[1] if len(row) > 1 else ""
    cat_val = row[2] if len(row) > 2 else "Other"
    try:
        amt_val = int(row[3]) if len(row) > 3 else 0
    except ValueError:
        amt_val = row[3] if len(row) > 3 else 0
    type_val = row[4] if len(row) > 4 else "Exp."

    existing_rows_formatted.append([date_val, item_val, cat_val, amt_val, type_val])

# Gabungkan data: Header + Data Excel Historis + Data Terbaru Hari Ini
header = ["Tanggal", "Item", "Kategori", "Nominal", "Tipe"]
all_rows_to_save = [header] + prepared_rows + existing_rows_formatted

print(f"🚀 Menyimpan total {len(all_rows_to_save)} baris (termasuk header) ke Google Sheets...")
ws.clear()
ws.update("A1", all_rows_to_save)
print("🎉 Selesai! Seluruh data sukses diimpor dan terstruktur rapi di Google Sheets.")
