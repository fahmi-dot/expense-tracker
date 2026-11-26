# Expense Tracker

Aplikasi lokal Flask + SQLite untuk mencatat pengeluaran.

## Jalankan
```bash
python -m pip install -r requirements.txt
python app.py
```
Buka http://127.0.0.1:5000. Database dibuat di `data/expenses.sqlite3`. Set `DATABASE_PATH` untuk lokasi lain.

## Test
```bash
PYTHONPATH=. pytest
```
Fitur: CRUD pengeluaran dan kategori, validasi server, ringkasan harian/bulanan, ekspor CSV semua/bulan/rentang, persistence SQLite.
