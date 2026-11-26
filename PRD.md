# PRD: Aplikasi Pencatat Pengeluaran Harian

## 1. Overview
Aplikasi lokal untuk satu pengguna mencatat dan mengelola pengeluaran, mengatur kategori, melihat total harian serta ringkasan bulanan, dan mengekspor data ke CSV. Masalah yang diselesaikan: pengguna perlu catatan pengeluaran terpusat yang bisa ditinjau dan dibawa keluar tanpa proses kompleks. Aplikasi memakai server-rendered Flask + Jinja dan SQLite sesuai pendekatan yang disetujui; berjalan lokal tanpa login.

## 2. Goals and Success Metrics
- Pengguna dapat mencatat pengeluaran dengan tanggal, kategori, nominal, dan keterangan opsional.
- Pengguna dapat melihat jumlah pengeluaran untuk hari yang dipilih dan ringkasan bulanan.
- Pengguna dapat mengelola kategori dan mengunduh data pengeluaran sebagai CSV.
- Sukses terukur: seluruh acceptance criteria pada dokumen ini lulus; ekspor CSV memuat data yang sesuai filter/periode yang dipilih.

## 3. Non-Goals
- Multi-user, akun, autentikasi, atau sinkronisasi daring.
- Anggaran, target tabungan, utang, pemasukan, atau laporan pajak.
- Impor CSV, lampiran struk, grafik analitik, dan notifikasi.
- Aplikasi seluler native atau hosting publik.

## 4. Users and Use Cases
**Pengguna utama:** satu orang yang mengelola catatan pengeluarannya sendiri secara lokal.
- Menambahkan transaksi setelah berbelanja.
- Memperbaiki atau menghapus transaksi keliru.
- Meninjau total pengeluaran pada tanggal tertentu dan ringkasan bulan tertentu.
- Menambah, mengubah nama, atau menghapus kategori.
- Mengunduh transaksi dalam CSV untuk digunakan di luar aplikasi.

## 5. Functional Requirements
| ID | Deskripsi | Prioritas | Kriteria penerimaan |
|---|---|---|---|
| FR-001 | Tambah pengeluaran dengan tanggal wajib, nominal wajib, kategori, dan keterangan opsional. | Must | Given data valid, when pengguna menyimpan, then transaksi baru tampil pada daftar dan total terkait diperbarui. |
| FR-002 | Validasi input pengeluaran. | Must | Tanggal wajib dan valid; nominal harus bilangan bulat positif; kategori harus tersedia; input tidak valid ditolak, pesan kesalahan ditampilkan, dan tidak ada transaksi tersimpan. |
| FR-003 | Tampilkan daftar pengeluaran dengan tanggal, kategori, nominal, dan keterangan bila ada. | Must | Given satu atau lebih transaksi, when daftar dibuka, then setiap transaksi menampilkan nilai yang tersimpan dan tersedia tindakan edit/hapus. |
| FR-004 | Edit transaksi yang ada. | Must | Given transaksi ada dan perubahan valid, when disimpan, then hanya transaksi terpilih berubah dan daftar serta jumlah terkait mencerminkan perubahan. Input tidak valid tidak mengubah data. |
| FR-005 | Hapus transaksi dengan konfirmasi. | Must | Given transaksi ada, when pengguna mengonfirmasi hapus, then transaksi tidak lagi muncul dan agregat terkait diperbarui. Jika batal, transaksi tetap ada. |
| FR-006 | Kelola kategori: tambah, ubah nama, hapus. | Must | Pengguna dapat membuat kategori; nama kosong atau duplikat ditolak. Penghapusan kategori yang dipakai tidak boleh menghilangkan atau mengubah transaksi diam-diam; aplikasi menolak dan menjelaskan bahwa kategori masih digunakan. |
| FR-007 | Tampilkan total pengeluaran per hari. | Must | Given tanggal yang dipilih, when tampilan harian dibuka, then jumlah nominal semua transaksi pada tanggal tersebut ditampilkan; tanggal tanpa transaksi menunjukkan total nol. |
| FR-008 | Tampilkan ringkasan bulanan. | Must | Given bulan dan tahun yang dipilih, when ringkasan dibuka, then total pengeluaran bulan tersebut dan jumlah per kategori untuk transaksi bulan itu ditampilkan; kategori tanpa transaksi tidak wajib ditampilkan. |
| FR-009 | Ekspor transaksi ke CSV. | Must | Ketika ekspor diminta, file CSV valid dapat diunduh, berisi kolom tanggal, kategori, nominal, dan keterangan serta transaksi sesuai cakupan periode yang dipilih; karakter Unicode dan nilai teks tidak rusak. |
| FR-010 | Sediakan kategori bawaan. | Should | Pada penggunaan awal tersedia kategori umum yang dapat ditambah, diubah, dan dihapus jika tidak dipakai. Nama kategori bawaan final merupakan asumsi dan dapat disesuaikan. |

## 6. Non-Functional Requirements
| ID | Kebutuhan | Kriteria terukur |
|---|---|---|
| NFR-001 | Lokal dan tanpa autentikasi | Aplikasi digunakan pada satu lingkungan lokal; tidak meminta akun atau login. Tidak ada sinkronisasi layanan daring dalam ruang lingkup. |
| NFR-002 | Integritas data | Setelah tambah/edit/hapus berhasil, perubahan tetap tersedia setelah aplikasi dimulai ulang. Penolakan validasi tidak mengubah data tersimpan. |
| NFR-003 | Privasi | Data pengeluaran disimpan secara lokal; tidak dikirim ke layanan eksternal. |
| NFR-004 | Kejelasan validasi | Setiap input invalid yang diketahui menampilkan pesan yang menyebut field bermasalah dan alasan penolakan. |
| NFR-005 | Format mata uang dan tanggal | Mata uang ditampilkan dalam IDR; tanggal transaksi memakai tanggal kalender yang dapat dibaca pengguna dan konsisten dengan format input. |
| NFR-006 | Ketepatan agregat | Total harian dan bulanan dihitung dari transaksi yang tersimpan, dalam bilangan rupiah bulat, tanpa pembulatan pecahan. |

## 7. User Flows
### Tambah pengeluaran
1. Pengguna membuka formulir tambah.
2. Mengisi tanggal, nominal, kategori, dan keterangan opsional.
3. Menyimpan.
4. Jika valid, aplikasi menyimpan dan menampilkan transaksi serta agregat terbaru.
5. Jika tanggal kosong/tidak valid, nominal bukan bilangan bulat positif, atau kategori tidak tersedia, aplikasi menampilkan kesalahan dan mempertahankan input yang aman untuk diperbaiki; data tidak disimpan.

### Edit atau hapus
1. Pengguna memilih transaksi dari daftar.
2. Untuk edit, mengubah satu atau lebih nilai lalu menyimpan; validasi sama dengan tambah.
3. Untuk hapus, memilih tindakan hapus lalu mengonfirmasi.
4. Batal tidak mengubah data; konfirmasi menghapus transaksi dan memperbarui daftar serta agregat.

### Lihat ringkasan
1. Pengguna memilih tanggal untuk total harian atau bulan/tahun untuk ringkasan bulanan.
2. Aplikasi menampilkan total dan rincian sesuai periode.
3. Periode tanpa data menampilkan nol dan keadaan kosong yang jelas, bukan error.

### Kelola kategori
1. Pengguna membuka pengelolaan kategori dan menambah atau mengubah nama kategori.
2. Nama kosong atau duplikat ditolak.
3. Saat menghapus kategori, aplikasi menolak penghapusan jika transaksi masih merujuk padanya dan memberi alasan; kategori yang tidak dipakai dapat dihapus.

### Ekspor CSV
1. Pengguna memilih periode ekspor yang tersedia.
2. Meminta ekspor.
3. Aplikasi mengunduh CSV dengan header konsisten dan data transaksi sesuai cakupan pilihan.
4. Jika tidak ada transaksi dalam cakupan, file tetap memiliki header dan tidak memiliki baris transaksi.

## 8. Constraints and Dependencies
- Teknologi dan pendekatan yang disetujui: Python + Flask, server-rendered Flask + Jinja, SQLite.
- Aplikasi untuk satu pengguna, berjalan lokal, tanpa login.
- Mata uang default IDR; tanggal transaksi wajib; nominal bilangan bulat positif.
- Kategori bawaan dapat ditambah, diubah, dan dihapus.
- Tidak ada batas waktu atau integrasi eksternal yang dinyatakan.

## 9. Assumptions
- A-001: Data disimpan hanya pada mesin lokal dan tidak perlu berbagi antarperangkat.
- A-002: Tanggal transaksi adalah tanggal kalender, bukan waktu/jam transaksi.
- A-003: Keterangan bersifat opsional; panjang maksimum belum ditetapkan dan perlu batas wajar pada implementasi.
- A-004: Penghapusan kategori yang masih dipakai ditolak, bukan menghapus/mengubah histori transaksi.
- A-005: Ekspor mencakup seluruh transaksi secara default atau periode yang dipilih; pemilih periode disediakan agar keluaran terkendali.
- A-006: Nama kategori tidak peka huruf besar/kecil saat memeriksa duplikasi.
- A-007: Kategori bawaan awal dapat berupa Makanan, Transportasi, Belanja, Tagihan, Kesehatan, dan Lainnya; daftar ini asumsi, bukan keputusan riset.

## 10. Risks
| Risiko | Kemungkinan | Dampak | Mitigasi |
|---|---|---|---|
| Berkas database lokal hilang atau rusak | Sedang | Tinggi: histori hilang | Beri petunjuk lokasi data dan sediakan ekspor CSV sebagai salinan; kebijakan backup belum termasuk MVP. |
| Perilaku kategori saat dihapus tidak sesuai harapan | Sedang | Sedang | Tolak penghapusan kategori yang masih dipakai dan jelaskan tindakan yang diperlukan. |
| CSV dibuka berbeda oleh aplikasi spreadsheet | Sedang | Sedang | Gunakan header tetap, encoding Unicode, dan format nilai/tanggal terdokumentasi; uji file hasil ekspor. |
| Kesalahan tanggal/bulan menyebabkan agregat salah | Rendah | Tinggi | Tetapkan semantik tanggal kalender dan uji batas awal/akhir bulan serta tahun kabisat. |
| Data lokal dapat diakses pengguna lain pada mesin yang sama | Rendah | Sedang | Ruang lingkup mengasumsikan satu pengguna; aplikasi tidak menyediakan autentikasi atau proteksi akses tambahan. |

## 11. Open Questions
1. Apakah penghapusan kategori yang masih digunakan harus ditolak (default rekomendasi), atau transaksi lama perlu dipindahkan ke kategori lain?
2. Apakah ekspor CSV harus selalu semua data atau perlu pemilihan rentang tanggal/bulan (default rekomendasi: semua data sebagai pilihan standar, dengan filter periode opsional)?
3. Format tampilan tanggal apa yang diinginkan (default rekomendasi: `YYYY-MM-DD` untuk konsistensi)?
4. Apakah pengguna memerlukan pencarian/filter daftar transaksi selain pemilihan periode (default rekomendasi: tidak untuk MVP)?

## 12. Acceptance Criteria Summary
- Pengguna dapat menambah, melihat, mengedit, dan menghapus pengeluaran yang valid.
- Sistem menolak tanggal kosong/tidak valid, nominal nol/negatif/pecahan/nonangka, kategori tidak tersedia, serta kategori kosong/duplikat; tidak ada perubahan data saat validasi gagal.
- Pengguna dapat mengelola kategori; kategori yang masih dipakai tidak dapat dihapus diam-diam.
- Total harian serta ringkasan bulanan dan per kategori cocok dengan penjumlahan transaksi pada periode yang benar, termasuk periode kosong dan batas bulan/tahun.
- CSV dapat diunduh dengan header dan data yang sesuai cakupan, termasuk kasus tanpa transaksi dan teks Unicode.
- Data bertahan setelah aplikasi lokal dimulai ulang; tidak diperlukan login atau koneksi layanan eksternal.
- Implementasi tetap dalam pendekatan yang disetujui: Flask + Jinja + SQLite, lokal, single-user.
