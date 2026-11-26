# Status

- Stage: Programmer
- Status: Selesai; defect D-01 sampai D-04 dan bonus warning diperbaiki, D-05 diperbaiki dengan halaman konfirmasi server-side
- Deliverable: `app.py`, `templates/confirm_delete.html`, `templates/list.html`, regression tests
- Verifikasi: `pytest -q tests/test_app.py tests/qa_probe.py` — 6 passed
- Catatan: Validasi tanggal/filter kini strict; missing ID return 404; delete wajib konfirmasi server-side.
