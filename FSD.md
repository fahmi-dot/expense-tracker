# Functional Specification Document (FSD)
## Aplikasi Pencatat Pengeluaran Harian

**PRD acuan:** `PRD.md` versi yang tersedia di workspace, termasuk FR-001–FR-010, NFR-001–NFR-006.
**Status dokumen:** desain implementasi; tidak mencakup kode produksi.

## 1. Overview dan Scope

Aplikasi lokal single-user untuk mencatat, meninjau, mengubah, menghapus pengeluaran, mengelola kategori, melihat total harian/ringkasan bulanan, dan mengekspor transaksi ke CSV. Implementasi memakai Python + Flask, server-rendered Jinja, dan SQLite. Tidak ada login, multi-user, sinkronisasi daring, integrasi eksternal, atau fitur non-goal PRD.

Semua nominal disimpan sebagai integer rupiah. Tanggal transaksi berupa tanggal kalender tanpa waktu. Data hanya berada pada database SQLite lokal.

## 2. Design Decisions

| Keputusan | Rancangan | Alasan / alternatif ditolak |
|---|---|---|
| Web stack | Flask dengan route server-rendered dan Jinja | Sesuai constraint PRD; SPA/REST-only menambah kompleksitas tanpa kebutuhan.
| Penyimpanan | SQLite satu file lokal dengan foreign key aktif | Persisten, ringan, tanpa server DB; PostgreSQL/MySQL tidak perlu untuk single-user lokal.
| Akses DB | Modul utilitas koneksi dan query terparameterisasi | Memisahkan akses data, mencegah SQL injection, dan cukup untuk domain kecil; ORM tidak ditambahkan tanpa kebutuhan.
| Identitas kategori | Foreign key `expenses.category_id` | Menjaga histori tetap valid dan memungkinkan penolakan penghapusan kategori terpakai.
| Nominal | `INTEGER`, rupiah bulat positif | Menghindari floating-point dan memenuhi NFR-006.
| Validasi | Validasi server sebagai sumber kebenaran; atribut HTML hanya bantuan UX | Request dapat dipalsukan; validasi client-only tidak aman.
| CSV | Modul standard library `csv`, respons streaming/attachment UTF-8 | Tidak perlu dependency tambahan; quoting menangani koma, newline, dan Unicode.
| Agregat | Query SQL `SUM` dan `GROUP BY` pada periode kalender | Total selalu berasal dari data tersimpan; tanpa cache yang berisiko basi.
| Konfirmasi hapus | Form POST terpisah dengan konfirmasi browser/halaman | Hapus tidak terjadi akibat GET; tetap sederhana tanpa JavaScript wajib.

## 3. Architecture

```text
Browser
  │ HTTP GET/POST
  ▼
Flask routes/controllers
  ├─ validation/domain rules
  ├─ flash message + redirect (POST/Redirect/GET)
  ├─ Jinja templates + CSS
  └─ CSV response
        │ parameterized SQL / transaction
        ▼
SQLite (categories, expenses)
```

Komponen:

- **App factory/config:** membuat Flask app, secret key lokal untuk flash message, path database, dan mendaftarkan route.
- **DB layer:** membuka koneksi per request, mengaktifkan `PRAGMA foreign_keys = ON`, menyediakan init/migration minimal, commit/rollback, dan penutupan koneksi.
- **Expense service/route logic:** CRUD expense, validasi tanggal/nominal/kategori, daftar, total harian, ringkasan bulanan.
- **Category service/route logic:** CRUD kategori, validasi nama, pemeriksaan referensi sebelum delete.
- **Export route:** validasi filter periode, mengambil data terurut, menulis CSV UTF-8 dengan header tetap.
- **Templates:** layout navigasi, form expense, daftar, dashboard harian/bulanan, dan kategori. Semua output user disafely escaped oleh Jinja default.

Transaksi DB: INSERT/UPDATE/DELETE dijalankan dalam satu transaksi dan commit hanya setelah validasi serta operasi berhasil. Error DB melakukan rollback dan menampilkan pesan generik.

## 4. Project Structure

Struktur minimum yang dibuat programmer:

```text
expense-tracker/
├── app.py                    # app factory/entry point Flask
├── config.py                 # konfigurasi environment dan default lokal
├── db.py                     # koneksi, schema init, transaction helpers
├── validators.py             # validasi dan normalisasi input
├── expenses.py               # route/use case expense dan agregat
├── categories.py             # route/use case category
├── export.py                 # route dan pembentukan CSV
├── schema.sql                # CREATE TABLE/index/seed idempoten
├── templates/
│   ├── base.html
│   ├── expenses/list.html
│   ├── expenses/form.html
│   ├── dashboard/daily.html
│   ├── dashboard/monthly.html
│   └── categories/list.html
├── static/
│   └── style.css
├── tests/
│   ├── test_validators.py
│   ├── test_expenses.py
│   ├── test_categories.py
│   ├── test_reports.py
│   └── test_export.py
└── data/                     # runtime database; jangan commit data pengguna
    └── expenses.sqlite3
```

Nama file boleh mengikuti konvensi repository bila repository kelak menyediakan struktur, tetapi tanggung jawab dan route contract tetap sama. `PRD.md`, `FSD.md`, dan `STATUS.md` tidak diubah oleh implementasi aplikasi.

## 5. Data Model

### 5.1 `categories`

| Kolom | Tipe | Constraint | Makna |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | ID internal stabil |
| `name` | TEXT | NOT NULL; UNIQUE secara case-insensitive | Nama kategori yang ditampilkan |
| `created_at` | TEXT | NOT NULL, default UTC ISO-8601 | Audit ringan; bukan data bisnis |

Unique case-insensitive wajib diwujudkan dengan index `UNIQUE INDEX ... ON categories(name COLLATE NOCASE)`. Nama disimpan setelah trim whitespace; nama kosong ditolak. Panjang maksimum implementasi: 100 karakter setelah trim (batas wajar untuk A-003; tidak ditetapkan PRD dan perlu dicatat sebagai asumsi).

### 5.2 `expenses`

| Kolom | Tipe | Constraint | Makna |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | ID internal transaksi |
| `expense_date` | TEXT | NOT NULL; format ISO `YYYY-MM-DD` | Tanggal kalender transaksi |
| `category_id` | INTEGER | NOT NULL; FK ke `categories(id)` ON DELETE RESTRICT | Kategori transaksi |
| `amount` | INTEGER | NOT NULL; CHECK (`amount > 0`) | Nominal rupiah bulat |
| `description` | TEXT | NOT NULL default `''` | Keterangan opsional, disimpan kosong bila tidak diisi |
| `created_at` | TEXT | NOT NULL, default UTC ISO-8601 | Waktu pencatatan teknis |
| `updated_at` | TEXT | NOT NULL, default UTC ISO-8601 | Waktu perubahan teknis |

Keterangan maksimum implementasi 500 karakter setelah normalisasi (asumsi eksplisit karena PRD belum menentukan batas). Index pada `expense_date` dan `category_id`. FK aktif setiap koneksi. Tidak ada cascade delete expense dari category; route menolak kategori yang masih direferensikan.

### 5.3 Seed dan migrasi

Saat database baru dibuat, seed kategori A-007: `Makanan`, `Transportasi`, `Belanja`, `Tagihan`, `Kesehatan`, `Lainnya`. Seed idempoten, tidak menduplikasi kategori yang sudah ada. Schema initialization tidak menghapus atau mengubah data. Perubahan schema berikutnya memakai migrasi additive/manual yang terdokumentasi; migrasi destruktif memerlukan persetujuan dan bukan bagian MVP.

## 6. Interfaces

### 6.1 Navigasi dan route Flask

| Method | Route | Input | Hasil |
|---|---|---|---|
| GET | `/` | query `date=YYYY-MM-DD` opsional; default hari ini | Redirect ke `/expenses?date=...` atau tampil daftar |
| GET | `/expenses` | `date` opsional untuk filter daftar; `month` opsional bila UI memerlukannya | Daftar transaksi, total periode/date yang dipilih, tombol tambah/edit/hapus |
| GET | `/expenses/new` | — | Form tambah |
| POST | `/expenses` | form `expense_date`, `amount`, `category_id`, `description` | 303 redirect ke daftar saat sukses; 400/form ulang saat invalid |
| GET | `/expenses/<int:id>/edit` | path ID | Form edit terisi; 404 bila tidak ada |
| POST | `/expenses/<int:id>` | field sama seperti tambah | Update atomik; 303 sukses, 400 invalid, 404 ID tidak ada |
| POST | `/expenses/<int:id>/delete` | token konfirmasi/form submit | Hapus setelah konfirmasi; 303; 404 bila tidak ada |
| GET | `/reports/daily` | query wajib/opsional `date=YYYY-MM-DD`; default hari ini | Total harian, daftar transaksi, keadaan kosong |
| GET | `/reports/monthly` | query `month=YYYY-MM`; default bulan berjalan | Total bulan dan total per kategori, keadaan kosong |
| GET | `/categories` | — | Daftar kategori, form tambah, aksi edit/hapus |
| POST | `/categories` | form `name` | Tambah kategori; 303 sukses atau 400 invalid |
| POST | `/categories/<int:id>` | form `name` | Ubah nama; 303 sukses atau 400/404 |
| POST | `/categories/<int:id>/delete` | form submit | Hapus jika tidak dipakai; tolak jika dipakai |
| GET | `/export.csv` | `date_from`, `date_to` opsional (`YYYY-MM-DD`) atau `month=YYYY-MM` | Attachment CSV UTF-8; 400 filter invalid |

POST sukses memakai PRG (Post/Redirect/Get) agar refresh tidak mengulang mutasi. Semua form mutasi memakai CSRF token bila dependency/implementasi CSRF tersedia; jika tidak, aplikasi lokal tetap wajib memeriksa method POST dan tidak menyediakan mutasi melalui GET.

### 6.2 Response dan format

- Sukses halaman: HTTP 200.
- Mutasi sukses: HTTP 303 ke halaman relevan.
- Input tidak valid: HTTP 400, form tampil ulang dengan nilai aman yang dikirim dan pesan per-field.
- Resource tidak ada: HTTP 404.
- Konflik kategori (nama duplikat atau kategori masih dipakai): HTTP 409 atau HTTP 400 yang konsisten; UI menyebut alasan konkret.
- Kegagalan internal/DB: HTTP 500, halaman error generik, detail dicatat di log tanpa data sensitif.
- Tampilan tanggal: `YYYY-MM-DD`. Mata uang: `Rp` dan pemisah ribuan lokal yang konsisten; nilai DB tetap integer.

### 6.3 Elemen UI utama

- Layout: navigasi ke Pengeluaran, Ringkasan Harian, Ringkasan Bulanan, Kategori, Ekspor.
- Form expense: tanggal wajib, nominal wajib, select kategori dari kategori aktif, keterangan opsional, pesan error dekat field, tombol simpan/batal.
- Daftar: tanggal, kategori, nominal IDR, keterangan bila tidak kosong, edit, hapus.
- Hapus: tombol submit POST dan dialog/halaman konfirmasi berisi identitas transaksi; batal tidak mengubah DB.
- Daily: date picker, total besar, daftar/empty state.
- Monthly: month picker, total bulan, tabel kategori dan total.
- Categories: daftar nama, form tambah, edit, hapus; pesan kategori terpakai.
- Export: pilihan semua data (default) atau rentang tanggal/bulan; tombol unduh; CSV kosong tetap tersedia.
- UI memakai label form, fokus keyboard, teks kontras, dan tidak bergantung pada JavaScript untuk fungsi inti.

## 7. Behavior dan Business Rules

### 7.1 Input expense

1. Ambil field POST dan trim text.
2. `expense_date` wajib dan harus dapat diparse tepat sebagai tanggal Gregorian valid dengan format `YYYY-MM-DD`; tanggal seperti `2024-02-30` ditolak.
3. `amount` wajib berupa string integer desimal tanpa pecahan, setelah trim; hanya nilai `> 0` diterima. `0`, negatif, pecahan, not-a-number, dan overflow ditolak.
4. `category_id` wajib integer dan harus menunjuk kategori yang ada.
5. `description` boleh kosong; trim; tolak bila melebihi 500 karakter.
6. Bila ada error, jangan jalankan INSERT/UPDATE; tampilkan pesan field spesifik dan pertahankan input non-rahasia.
7. Bila valid, simpan dalam satu transaksi; redirect dan hitung ulang agregat dari DB.

Aturan edit sama dengan tambah. Update memakai `WHERE id = ?`; ID tidak ditemukan menghasilkan 404 dan tidak membuat row baru.

### 7.2 Delete expense

GET tidak menghapus. POST hanya menghapus ID yang ada setelah pengguna mengonfirmasi. Batal tidak mengirim mutasi. Setelah commit, daftar dan agregat berikutnya membaca DB terbaru.

### 7.3 Category

- Nama trim, wajib tidak kosong, maksimum 100 karakter.
- Duplikasi dibandingkan case-insensitive (`Makanan` sama dengan `makanan`), termasuk terhadap kategori lain saat edit.
- Tambah/edit invalid tidak mengubah DB.
- Delete kategori melakukan pemeriksaan `EXISTS` pada `expenses.category_id`; bila ada transaksi, tolak dan jelaskan bahwa kategori masih digunakan. Bila tidak ada, hapus atomik.
- Jika ID kategori hilang saat submit expense, validasi gagal; transaksi tidak tersimpan.

### 7.4 Reports

- Daily memakai rentang inklusif satu tanggal: `expense_date = selected_date`.
- Monthly memakai `YYYY-MM` sebagai rentang `[hari pertama bulan, hari pertama bulan berikutnya)`, aman untuk tahun baru dan tahun kabisat.
- `SUM` kosong dipetakan ke 0. Ringkasan per kategori hanya menampilkan kategori dengan transaksi.
- Periode tanpa data menampilkan total `Rp0` dan empty state, bukan error.

### 7.5 CSV

- Default ekspor semua transaksi bila filter kosong.
- Rentang tanggal mensyaratkan kedua endpoint `date_from` dan `date_to`; keduanya valid dan `from <= to`.
- Filter bulan memakai seluruh bulan kalender.
- Query mengurutkan `expense_date ASC, id ASC`.
- Header tetap: `tanggal,kategori,nominal,keterangan`.
- Nilai tanggal ISO, nominal integer rupiah tanpa simbol, kategori dan keterangan teks asli setelah normalisasi.
- Gunakan `csv.writer` dengan `newline=''`, UTF-8 (opsional BOM hanya bila keputusan kompatibilitas spreadsheet diambil; default UTF-8 tanpa BOM). Nilai Unicode, koma, quote, dan newline harus di-quote sesuai CSV.
- Tanpa transaksi: file tetap memiliki header tanpa baris data.

## 8. Error Handling dan Logging

Pesan UI harus spesifik: `Tanggal wajib dan harus berformat YYYY-MM-DD`, `Nominal harus bilangan bulat lebih besar dari 0`, `Pilih kategori yang tersedia`, `Nama kategori sudah digunakan`, atau `Kategori masih digunakan oleh transaksi dan tidak dapat dihapus`.

Kategori error:

- **ValidationError:** form 400, tidak menulis DB.
- **NotFound:** 404, tidak menulis DB.
- **Conflict:** 409/400 konsisten untuk duplikat/referensi aktif.
- **DatabaseError:** rollback, log stack trace server-side, tampilkan error generik dan jangan bocorkan SQL/path internal.
- **ExportError:** respons error generik; tidak menghasilkan file parsial yang diklaim sukses.

Log hanya event teknis, route, status, durasi, dan ID internal bila perlu. Jangan log seluruh request form, nominal/keterangan pengguna, cookie/secret, atau isi CSV. Jangan menampilkan traceback pada mode produksi lokal yang dipakai pengguna.

## 9. Security dan Privacy

- Tidak ada autentikasi sesuai NFR-001; server bind default ke localhost, bukan interface publik.
- Semua SQL memakai parameter binding; jangan interpolasi input ke query.
- Validasi server untuk semua route POST dan filter GET.
- Jinja autoescape aktif untuk teks kategori/keterangan.
- Method mutasi hanya POST; aktifkan CSRF token untuk proteksi request lintas situs bila menggunakan extension CSRF.
- Secret key hanya dari environment/default lokal acak untuk runtime; jangan commit secret.
- Database dan CSV tetap lokal; tidak ada HTTP call eksternal/telemetri.
- Escape/quote CSV mencegah korupsi kolom; pertimbangkan formula injection pada implementasi bila spreadsheet menjadi target, tanpa mengubah nilai bisnis secara diam-diam.
- File database diberi permission OS yang wajar; backup bukan fitur MVP. Jangan menaruh data runtime di Git.

## 10. Configuration dan Environment

Variabel konfigurasi:

- `FLASK_APP`: entry point aplikasi.
- `FLASK_ENV` atau mode debug Flask: debug hanya development, nonaktif saat penggunaan normal.
- `SECRET_KEY`: secret sesi/flash, jangan hardcode production.
- `DATABASE_PATH`: path absolut/relatif database SQLite lokal.
- `HOST`: default `127.0.0.1`.
- `PORT`: port lokal aplikasi.

Dependency utama: Python versi yang kompatibel dengan Flask yang dipilih, Flask versi yang dikunci di `requirements.txt`, dan SQLite bawaan Python. Versi Flask/Python final harus diverifikasi saat setup proyek; FSD tidak mengklaim versi yang belum ditetapkan. Extension CSRF hanya ditambahkan bila dipilih implementasi dan versinya dikunci.

## 11. Test Strategy

Gunakan temporary SQLite database per test; tidak pernah memakai database pengguna. Test app Flask dengan mode testing dan client HTTP.

### Unit

- Parser tanggal menerima tanggal valid, menolak kosong, format salah, tanggal kalender invalid, batas tahun kabisat.
- Parser nominal menerima integer positif, menolak nol/negatif/pecahan/nonangka/overflow.
- Validator kategori dan deskripsi: kosong, trim, duplikat case-insensitive, batas panjang.
- Rentang daily/monthly benar pada awal/akhir bulan, pergantian tahun, Februari kabisat.
- CSV quoting untuk Unicode, koma, quote, newline, dan dataset kosong.

### Integration/API

- Tambah valid menyimpan row; daftar menampilkan data; restart app tetap membaca row.
- Semua invalid expense menghasilkan 400, pesan field, dan count DB tidak berubah.
- Edit hanya row target; invalid edit tidak mengubah row.
- Delete confirmed menghapus; cancel tidak menghapus.
- Category CRUD; duplikat ditolak; category terpakai tidak dapat dihapus; category kosong dapat dihapus.
- Daily total dan monthly total/per-category cocok dengan penjumlahan integer.
- CSV header/data/filter/rentang/default dan Unicode benar.
- Error ID tidak ada menghasilkan 404; DB failure rollback dan tidak ada partial write.

### End-to-end/browser

- Alur tambah → daftar → edit → hapus.
- Alur kategori → pilih saat tambah → tolak delete saat terpakai.
- Alur daily/monthly dengan periode kosong menampilkan nol/empty state.
- Alur ekspor unduh file yang dapat diparse dan dibuka tanpa kolom rusak.
- Label, keyboard, konfirmasi hapus, dan pesan validasi terlihat pada template utama.

Test coverage wajib memetakan FR-001–FR-010 dan NFR-001–NFR-006 pada matriks berikut.

## 12. Implementation Order

1. Buat app factory, konfigurasi localhost, struktur template/static, dan test fixture.
2. Buat schema SQLite, FK/index, koneksi per request, init idempoten, dan seed kategori.
3. Implement validator tanggal, nominal, kategori, nama, deskripsi; tulis unit test.
4. Implement category list/add/edit/delete beserta constraint referensi.
5. Implement expense add/list/edit/delete dengan PRG dan pesan error.
6. Implement daily/monthly queries dan halaman ringkasan.
7. Implement CSV filter, serialization UTF-8, dan download.
8. Tambah hardening security, logging, empty states, accessibility UI.
9. Jalankan unit, integration, dan end-to-end test; verifikasi restart persistence dan seluruh traceability matrix.

## 13. Traceability Matrix

| PRD ID | FSD section | Planned tests |
|---|---|---|
| FR-001 | 5, 6.1, 7.1 | `test_add_valid_expense`, list shows saved row and updated total |
| FR-002 | 5.2, 6.2, 7.1, 8 | invalid date/amount/category tests; DB unchanged assertions |
| FR-003 | 6.3, 7.1 | list fields, optional description, edit/delete controls |
| FR-004 | 6.1, 7.1 | valid targeted update; invalid update leaves original row |
| FR-005 | 6.1, 6.3, 7.2 | confirmed delete, cancel delete, aggregate refresh |
| FR-006 | 5.1, 5.2, 6.1, 7.3 | category CRUD, blank/duplicate rejection, in-use delete rejection |
| FR-007 | 6.1, 6.3, 7.4 | selected day, zero day, date boundary tests |
| FR-008 | 6.1, 6.3, 7.4 | monthly total/per-category, empty month, leap/year boundary |
| FR-009 | 6.1, 7.5 | header, filters, empty export, Unicode/CSV quoting |
| FR-010 | 5.3, 7.3 | first-run seed, seed idempotency, edit/delete unused defaults |
| NFR-001 | 2, 3, 9, 10 | local startup; no login/external request; localhost bind |
| NFR-002 | 5.3, 7, 8 | restart persistence; rollback on validation/DB failure |
| NFR-003 | 3, 9 | network isolation/mock verifies no external calls |
| NFR-004 | 6.2, 7.1, 7.3, 8 | each invalid field gets reason-specific visible message |
| NFR-005 | 6.2, 6.3 | IDR display and consistent `YYYY-MM-DD` input/output |
| NFR-006 | 5.2, 7.4 | integer sum, no rounding, daily/monthly boundary cases |

## 14. Risks, Assumptions, dan Open Issues

### Assumptions

- A-001 sampai A-006 dari PRD diterapkan: data lokal, tanggal kalender, category delete ditolak bila terpakai, filter ekspor tersedia, dan duplicate category case-insensitive.
- A-007 seed kategori memakai enam nama yang dicantumkan PRD.
- Batas 100 karakter kategori dan 500 karakter keterangan adalah asumsi implementasi karena PRD belum menetapkannya; programmer harus menjaga nilai ini mudah diubah tanpa migrasi.
- Tampilan tanggal default `YYYY-MM-DD`; ekspor default semua data dengan filter opsional.
- `ON DELETE RESTRICT` dan pemeriksaan eksplisit route dipakai bersama agar tidak ada perubahan histori diam-diam.

### Open issues untuk Hermes/owner

1. PRD masih mencantumkan pertanyaan terbuka tentang pilihan ekspor, format tanggal, dan perilaku delete kategori, tetapi bagian assumptions/acceptance sudah memberi default. FSD memakai default tersebut; owner perlu mengesahkan bila berbeda.
2. Batas panjang keterangan belum ditetapkan PRD. FSD mengasumsikan 500 karakter. Ubah bila kebutuhan bisnis punya batas lain.
3. Format mata uang hanya menyebut IDR, belum menetapkan separator tampilan dan BOM CSV. FSD menetapkan tampilan IDR konsisten, integer CSV UTF-8 tanpa BOM; keputusan kompatibilitas spreadsheet dapat mengubah detail ini tanpa mengubah data.
4. Kebijakan backup database belum termasuk MVP. Risiko kehilangan file tetap ada; ekspor CSV diperlakukan sebagai salinan manual, bukan backup otomatis.
5. Tanpa autentikasi, pengguna lain yang memiliki akses OS dapat membaca database; ini batas eksplisit NFR-001/NFR-003, bukan celah yang ditutup dalam scope.

Tidak ada kebutuhan Must yang tidak tercakup. Tidak ada kode produksi dibuat dalam dokumen ini.
