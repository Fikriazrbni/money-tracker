# 🚀 Panduan Deploy Bot Keuangan ke Hosting Gratis (Render)

Bot ini jalan terus-menerus (`infinity_polling`), jadi kita deploy sebagai
**Background Worker** di [Render.com](https://render.com) — gratis dan tidak butuh kartu kredit.

---

## ⚠️ LANGKAH 0 — Amankan Kredensial (WAJIB, lakukan dulu!)

Token & key kamu sudah pernah tampil di file `.env`. Sebelum deploy, ganti dulu biar aman:

1. **Telegram Token** → buka chat [@BotFather](https://t.me/BotFather) → `/token` atau `/revoke` → salin token baru.
2. **Gemini API Key** → buka [Google AI Studio](https://aistudio.google.com/apikey) → hapus key lama, buat key baru.
3. **JANGAN** commit file `.env` dan `credentials.json` ke GitHub. (`.gitignore` sudah mengatur ini.)

---

## LANGKAH 1 — Siapkan Akun

1. Buat akun [GitHub](https://github.com) (kalau belum punya).
2. Buat akun [Render](https://render.com) → login pakai GitHub (paling gampang).

---

## LANGKAH 2 — Push Project ke GitHub

Dari folder project, jalankan di terminal:

```bash
git init
git add .
git commit -m "Deploy bot keuangan"
```

> Pastikan `.env` dan `credentials.json` **TIDAK** muncul saat `git status`.
> Kalau muncul, berarti `.gitignore` belum terbaca — cek lagi.

Buat repo baru di GitHub (boleh **Private**), lalu hubungkan:

```bash
git branch -M main
git remote add origin https://github.com/USERNAME/NAMA-REPO.git
git push -u origin main
```

---

## LANGKAH 3 — Buat Service di Render

1. Di dashboard Render, klik **New +** → **Background Worker**.
2. Pilih repo GitHub yang baru kamu push.
3. Isi konfigurasi:
   - **Name**: bebas (misal `bot-keuangan`)
   - **Region**: Singapore (paling dekat Indonesia)
   - **Runtime / Language**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Instance Type**: **Free**

---

## LANGKAH 4 — Isi Environment Variables

Di halaman setup Render, buka bagian **Environment** → **Add Environment Variable**.
Tambahkan satu per satu:

| Key                | Value                                                        |
|--------------------|-------------------------------------------------------------|
| `TELEGRAM_TOKEN`   | token baru dari BotFather                                    |
| `GEMINI_API_KEY`   | API key baru dari Google AI Studio                          |
| `SPREADSHEET_NAME` | `MonTracker` (sesuaikan dengan nama Google Sheet kamu)      |
| `ALLOWED_USER_ID`  | ID Telegram kamu (angka, contoh `530532204`)                |
| `GOOGLE_CREDENTIALS` | **seluruh isi file `credentials.json`** (lihat Langkah 5) |

---

## LANGKAH 5 — Isi `GOOGLE_CREDENTIALS`

Karena file `credentials.json` tidak boleh di-upload, isinya kita tempel sebagai 1 variable.

1. Buka file `credentials.json` di komputer kamu.
2. **Copy seluruh isinya** (dari `{` sampai `}`).
3. Tempel sebagai value dari variable `GOOGLE_CREDENTIALS` di Render.

> Tip: tempel apa adanya (boleh JSON multi-baris). Kode sudah mem-parse-nya otomatis.

---

## LANGKAH 6 — Deploy & Cek

1. Klik **Create Background Worker** (atau **Deploy**).
2. Tunggu build selesai (lihat tab **Logs**).
3. Kalau sukses, log akan menampilkan:
   ```
   ✅ Terkoneksi ke Google Sheets: MonTracker
   🚀 Bot siap berjalan!
   ```
4. Buka Telegram, chat bot kamu: `/start` lalu coba `beli kopi 25k`.

---

## 🧰 Troubleshooting

- **Bot tidak balas** → cek tab **Logs** di Render. Error paling umum: token salah atau `ALLOWED_USER_ID` tidak cocok.
- **"Gagal konek ke Google Sheets"** → pastikan:
  - `GOOGLE_CREDENTIALS` berisi JSON lengkap (tidak terpotong).
  - Email service account (ada di dalam credentials, field `client_email`) sudah di-**Share** sebagai Editor di Google Sheet kamu.
- **Worker "spin down"** → Background Worker di free tier Render tetap jalan, tapi punya kuota jam/bulan. Kalau habis, worker berhenti sampai bulan berikutnya. Untuk uji coba ini cukup.

---

## Alternatif Hosting Gratis Lain

- **Railway** (`railway.app`) — mirip, pakai Procfile yang sudah ada.
- **Fly.io** — gratis tapi butuh sedikit setup Docker.

Render dipilih karena paling simpel untuk bot polling seperti ini.
