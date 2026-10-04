import os
import telebot
import gspread
import json
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "MonTracker").strip()
raw_user_id = os.getenv("ALLOWED_USER_ID", "").strip()
ALLOWED_USER_ID = int(raw_user_id) if raw_user_id.isdigit() else 0

# Validasi token Telegram
if not TELEGRAM_TOKEN or ":" not in TELEGRAM_TOKEN:
    print("❌ Error: TELEGRAM_TOKEN belum diisi atau tidak valid di file .env!")
    print("💡 Contoh format token: TELEGRAM_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Inisialisasi Google GenAI
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("⚠️ Peringatan: GEMINI_API_KEY belum diisi di .env!")

if ALLOWED_USER_ID == 0:
    print("ℹ️ Catatan: ALLOWED_USER_ID masih kosong. Bot akan menolak chat sampai kamu mengisi ID Telegram di .env.")

# Inisialisasi Google Sheets
# Mendukung 2 sumber kredensial:
# 1. Environment variable GOOGLE_CREDENTIALS (berisi isi JSON) -> dipakai saat deploy di hosting.
# 2. File credentials.json -> dipakai saat development lokal.
worksheet = None
try:
    gc = None
    google_creds_env = os.getenv("GOOGLE_CREDENTIALS", "").strip()

    if google_creds_env and SPREADSHEET_NAME:
        creds_dict = json.loads(google_creds_env)
        gc = gspread.service_account_from_dict(creds_dict)
        print("✅ Memuat kredensial Google dari environment variable.")
    elif os.path.exists("credentials.json") and SPREADSHEET_NAME:
        gc = gspread.service_account(filename="credentials.json")
        print("✅ Memuat kredensial Google dari file credentials.json.")
    else:
        print("⚠️ Catatan: GOOGLE_CREDENTIALS/credentials.json belum ada atau SPREADSHEET_NAME belum diisi.")

    if gc:
        sh = gc.open(SPREADSHEET_NAME)
        worksheet = sh.sheet1
        print("✅ Terkoneksi ke Google Sheets:", SPREADSHEET_NAME)
except Exception as e:
    print(f"⚠️ Peringatan: Gagal konek ke Google Sheets. Error: {e}")

# Daftar model untuk auto-fallback jika salah satu model sedang high-demand (503)
MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-flash-lite"]

CATEGORIES = [
    "🍜 Food",
    "☕ Coffee",
    "🚖 Transport",
    "🛒 Groceries",
    "🪑 Stuff home",
    "🎁 Gift & Social",
    "🧖 Chilling n Healing",
    "💳 Subscriptions",
    "🛠️ Services",
    "🧥 Apparel",
    "🏥 Healthy & Medical",
    "🧑‍⚕️ body care",
    "🏃 Sport",
    "💰 Salary",
    "🏅 Bonus",
    "Other"
]

def format_idr(amount):
    """Format angka ke format rupiah Indonesia (contoh: 25.000)"""
    return f"{amount:,}".replace(",", ".")

def detect_target_month(text):
    """Mendeteksi bulan yang dimaksud dari pertanyaan user."""
    text_lower = text.lower()
    now = datetime.now()

    if "bulan lalu" in text_lower or "last month" in text_lower:
        prev_month = 12 if now.month == 1 else now.month - 1
        prev_year = now.year - 1 if now.month == 1 else now.year
        return f"{prev_year:04d}-{prev_month:02d}"

    indonesian_months = {
        "januari": "01", "februari": "02", "maret": "03", "april": "04",
        "mei": "05", "juni": "06", "juli": "07", "agustus": "08",
        "september": "09", "oktober": "10", "november": "11", "desember": "12"
    }
    for m_name, m_num in indonesian_months.items():
        if m_name in text_lower:
            return f"{now.year:04d}-{m_num}"

    return now.strftime("%Y-%m")

def get_rekap_report(target_month=None):
    """Menghitung rekap total pengeluaran, pemasukan, dan rincian per kategori."""
    if not worksheet:
        return "❌ Spreadsheet belum terkoneksi. Periksa credentials.json."

    if not target_month:
        target_month = datetime.now().strftime("%Y-%m")

    all_vals = worksheet.get_all_values()
    if len(all_vals) <= 1:
        return "ℹ️ Belum ada transaksi yang tercatat di spreadsheet."

    rows = all_vals[1:]
    total_exp = 0
    total_inc = 0
    cat_exp = defaultdict(int)
    tx_count = 0

    for r in rows:
        if not r or len(r) < 4:
            continue
        date_str = r[0]
        if not date_str.startswith(target_month):
            continue

        try:
            amt = int(str(r[3]).replace(",", "").replace(".", "").replace("Rp", "").strip())
        except Exception:
            continue

        type_str = r[4] if len(r) > 4 else "Exp."
        cat = r[2] if len(r) > 2 and r[2] else "Other"
        tx_count += 1

        if type_str == "Income":
            total_inc += amt
        else:
            total_exp += amt
            cat_exp[cat] += amt

    if tx_count == 0:
        return f"ℹ️ Belum ada transaksi yang tercatat untuk periode **{target_month}**."

    cashflow = total_inc - total_exp
    cashflow_icon = "🟢" if cashflow >= 0 else "🔴"
    cashflow_str = f"Rp {format_idr(cashflow)}" if cashflow >= 0 else f"-Rp {format_idr(abs(cashflow))}"

    try:
        dt = datetime.strptime(target_month, "%Y-%m")
        month_names = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        period_label = f"{month_names[dt.month - 1]} {dt.year}"
    except Exception:
        period_label = target_month

    lines = [
        f"📊 **REKAP KEUANGAN — {period_label.upper()}**\n",
        f"💸 **Total Pengeluaran:** Rp {format_idr(total_exp)}",
        f"💰 **Total Pemasukan:** Rp {format_idr(total_inc)}",
        f"{cashflow_icon} **Selisih / Sisa:** {cashflow_str}\n",
        "🏷️ **Rincian Pengeluaran per Kategori:**"
    ]

    for c, val in sorted(cat_exp.items(), key=lambda x: x[1], reverse=True):
        pct = (val / total_exp * 100) if total_exp > 0 else 0
        lines.append(f"• **{c}**: Rp {format_idr(val)} *({pct:.1f}%)*")

    lines.append(f"\n📝 *Total Transaksi: {tx_count} transaksi*")
    return "\n".join(lines)

def is_asking_for_rekap(text):
    """Cek cepat apakah pesan user bermaksud menanyakan rekap/pengeluaran."""
    text_lower = text.lower()
    rekap_triggers = [
        "rekap", "pengeluaran bulan", "expense bulan", "expanse bulan",
        "total pengeluaran", "habis berapa", "keluar berapa", "total belanja",
        "summary", "laporan", "sisa saldo", "pengeluaran kita", "expense kita", "expanse kita"
    ]
    return any(trigger in text_lower for trigger in rekap_triggers)

def parse_expense_with_gemini(user_text):
    if not client:
        return None, "API Key Gemini belum diset di .env"

    today_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
    Kamu asisten keuangan pintar. Tentukan apakah teks user adalah:
    1. PERTANYAAN REKAP/LAPORAN (misal: 'expense kita berapa bulan ini?', 'rekap dong', 'pengeluaran september berapa?')
    2. PENCATATAN TRANSAKSI BARU (misal: 'beli kopi 25k', 'gaji masuk 12jt')
    3. TEKS LAINNYA / TIDAK VALID (misal: 'halo', '.', 'tes')

    Tanggal hari ini: {today_date}.
    
    Pilihan Kategori untuk transaksi:
    - "🍜 Food", "☕ Coffee", "🚖 Transport", "🛒 Groceries", "🪑 Stuff home",
      "🎁 Gift & Social", "🧖 Chilling n Healing", "💳 Subscriptions", "🛠️ Services",
      "🧥 Apparel", "🏥 Healthy & Medical", "🧑‍⚕️ body care", "🏃 Sport", "💰 Salary",
      "🏅 Bonus", "Other"

    Format JSON yang harus dihasilkan:
    Jika PERTANYAAN REKAP:
    {{
      "is_rekap": true,
      "target_month": "{today_date[:7]}" // atau YYYY-MM sesuai bulan yang diminta user
    }}

    Jika PENCATATAN TRANSAKSI:
    {{
      "is_rekap": false,
      "is_valid": true,
      "type": "Exp." atau "Income",
      "item": "nama barang/jasa",
      "amount": integer harga bulat (contoh: 25k -> 25000, 100rb -> 100000, 1.5jt -> 1500000),
      "category": salah satu dari daftar kategori di atas beserta emojinya,
      "date": "{today_date}"
    }}

    Jika BUKAN KEDUANYA:
    {{
      "is_rekap": false,
      "is_valid": false
    }}

    Teks user: "{user_text}"
    """

    last_error = None
    for model_name in MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            raw = response.text.strip()
            data = json.loads(raw)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            if isinstance(data, dict):
                return data, None
        except Exception as e:
            last_error = e
            print(f"⚠️ Model {model_name} error ({e}). Mencoba model alternatif...")
            continue

    return None, f"Server Gemini sedang sibuk. Error: {last_error}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 **Halo! Gua bot keuangan lu.**\n\n"
        "💡 **Cara pakai:**\n"
        "1. **Catat Pengeluaran / Pemasukan:**\n"
        "   • `beli kopi susu 25k`\n"
        "   • `bensin motor 35rb`\n"
        "   • `gaji masuk 12jt`\n\n"
        "2. **Tanya Rekap & Laporan:**\n"
        "   • `pengeluaran bulan ini berapa?`\n"
        "   • `rekap bulan lalu`\n"
        "   • `rekap september`\n"
        "   • Atau ketik `/rekap`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['rekap', 'summary', 'laporan'])
def handle_rekap_command(message):
    if message.chat.id != ALLOWED_USER_ID:
        bot.reply_to(message, f"⛔ Maaf, lu gak punya akses ke bot ini. (ID Telegram lu: {message.chat.id})")
        return

    msg_loading = bot.reply_to(message, "⏳ Sedang menghitung rekap...")
    target_month = detect_target_month(message.text)
    report_text = get_rekap_report(target_month)
    bot.edit_message_text(chat_id=message.chat.id, message_id=msg_loading.message_id, text=report_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.chat.id != ALLOWED_USER_ID:
        bot.reply_to(message, f"⛔ Maaf, lu gak punya akses ke bot ini. (ID Telegram lu: {message.chat.id})")
        return

    msg_loading = bot.reply_to(message, "⏳ Sedang memproses...")

    # Cek apakah user menanyakan rekap secara langsung via keyword
    if is_asking_for_rekap(message.text):
        target_month = detect_target_month(message.text)
        report_text = get_rekap_report(target_month)
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg_loading.message_id, text=report_text, parse_mode="Markdown")
        return

    # Jika bukan keyword langsung, biarkan Gemini memproses maksudnya
    data, error_msg = parse_expense_with_gemini(message.text)

    if data:
        # Jika Gemini mendeteksi ini pertanyaan rekap
        if data.get("is_rekap"):
            target_month = data.get("target_month") or detect_target_month(message.text)
            report_text = get_rekap_report(target_month)
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg_loading.message_id, text=report_text, parse_mode="Markdown")
            return

        # Jika transaksi tidak valid
        if not data.get("is_valid", True) or not data.get("amount"):
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_loading.message_id,
                text="ℹ️ Maksud pesan tidak terdeteksi.\n• Untuk catat: `beli kopi 25k`\n• Untuk rekap: `pengeluaran bulan ini berapa?`",
                parse_mode="Markdown"
            )
            return

        # Simpan transaksi ke Google Sheets
        if not worksheet:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_loading.message_id,
                text="❌ Gagal: Spreadsheet belum terkoneksi (periksa credentials.json dan SPREADSHEET_NAME)."
            )
            return

        try:
            type_val = data.get("type", "Exp.")
            row_to_insert = [
                data.get("date"),
                data.get("item"),
                data.get("category"),
                data.get("amount"),
                type_val
            ]
            worksheet.append_row(row_to_insert, insert_data_option="INSERT_ROWS")

            type_label = "Pemasukan 💰" if type_val == "Income" else "Pengeluaran 💸"
            success_msg = (
                f"✅ **Berhasil dicatat ({type_label})!**\n\n"
                f"🛍️ Item: {data.get('item')}\n"
                f"🏷️ Kategori: {data.get('category')}\n"
                f"💵 Nominal: Rp {format_idr(data.get('amount', 0))}\n"
                f"📅 Tanggal: {data.get('date')}"
            )
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg_loading.message_id, text=success_msg, parse_mode="Markdown")
        except Exception as e:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg_loading.message_id, text=f"❌ Gagal nyimpen ke spreadsheet: {str(e)}")
    else:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg_loading.message_id,
            text=f"❌ Gagal memproses: {error_msg or 'Format tidak valid.'}"
        )

if __name__ == "__main__":
    print("🚀 Bot siap berjalan! Tekan Ctrl+C untuk berhenti.")
    bot.infinity_polling()
