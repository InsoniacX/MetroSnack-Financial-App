# Hutang bawaan antarbulan

Saldo dihitung ulang oleh backend setiap dibaca, berdasarkan urutan tahun dan
bulan folder pada cabang yang sama. Tidak ada penyalinan saldo ke invoice,
kolom/tabel baru, migration, atau perubahan otomatis pada data tersimpan.

    saldo_awal = sisa_hutang folder sebelumnya
    sisa_hutang = max(0, saldo_awal + invoice_bon + masuk_barang - masuk_uang)

PENTING: invoice_bon tetap nominal baru periode tersebut, bukan gabungan
dengan hutang lama. Sebelum menggunakan fitur pada data lama, periksa apakah
operator pernah memasukkan hutang sebelumnya secara manual ke invoice_bon.
Jika pernah, backup dan rekonsiliasi dahulu; sistem tidak dapat membedakan
komponen itu secara otomatis. Jangan mengubah data secara massal tanpa
memeriksa sumber invoice.

## Aturan

- Bulan pertama mulai dengan bawaan 0. Bulan kosong meneruskan saldo.
- Jika bulan dilewati, saldo dari periode sebelumnya yang tersedia diteruskan.
- Desember ke Januari mengikuti tahun, bukan waktu folder dibuat atau ID.
- Koreksi/penambahan mundur/penghapusan transaksi, invoice, atau folder
  memengaruhi saldo semua periode setelahnya saat dibaca kembali.
- Setelah lunas/lebih bayar, bawaan berikutnya 0. Kelebihan pembayaran tidak
  disimpan sebagai kredit antarbulan, mengikuti kebijakan hutang minimal 0.
- Untuk beberapa invoice dalam folder lama, mutasi dijumlahkan dahulu dan
  hutang bawaan ditambahkan sekali pada total folder, bukan per invoice.
- Dashboard menjumlahkan saldo akhir terbaru tiap cabang, bukan saldo seluruh
  bulan, dan bukan mengurangi hutang cabang A dengan lebih bayar cabang B.
- Omset, barang, dan modal pada dashboard tetap jumlah mutasi asli.
- Belum ada tutup buku atau push realtime. Buka ulang/refresh halaman untuk
  melihat koreksi terbaru dari pengguna lain. PDF lama harus diekspor ulang.

## API dan deployment

- GET /folders/saldo-hutang?cabang_id=...: semua saldo bulanan dalam satu batch.
- GET /folders/{id}/saldo-hutang: saldo akhir folder termasuk hutang bawaan.
- GET /invoices/{id}/full: header/transaksi tidak berubah, ditambah
  keuangan_folder dari backend.
- GET /invoices/{id}/sisa-hutang: sekarang saldo seluruh folder bulan invoice
  tersebut (cakupan=folder_bulan). Untuk folder satu invoice, modal/mutasi sama
  seperti sebelumnya. Untuk folder beberapa invoice, rincian_invoice berisi
  kalkulasi invoice itu saja tanpa bawaan.
- Dashboard dan monthly-trend menggunakan riwayat yang sama; limit grafik
  diterapkan setelah saldo seluruh periode sebelumnya dihitung.
- Hak akses cabang tetap diperiksa sebelum membaca riwayat.

Deploy/restart backend terlebih dahulu lalu client. Client baru menolak saldo
yang hilang dari backend lama, bukan diam-diam menampilkan nol. Generator PDF
invoice/folder membutuhkan keyword keuangan_folder dari backend. PDF cabang
menggunakan saldo akhir periode terakhir, bukan jumlah saldo semua periode.

## Verifikasi (PowerShell)

Dari direktori backend:

    .\venv\Scripts\python.exe -B -m pytest --noconftest -p no:cacheprovider -q tests/test_finance_service.py tests/test_debt_carry_forward.py tests/test_debt_postgres.py

Tes PostgreSQL hanya memakai TEMP tables dengan search_path=pg_temp pada
database lokal metrosnack_financial_test, selalu rollback, tidak menulis tabel
aplikasi/seed. Jika konfigurasi/koneksi test tidak tersedia, tes SQL dilewati
dengan alasan eksplisit. Tes rumus dan HTTP tiruan tetap dapat dijalankan.

Dari root proyek:

    .\client\venv\Scripts\python.exe -B -X utf8 -m unittest discover -s client/tests -p 'test_*.py' -v

Skenario manual: Agustus hutang 120 juta; September invoice baru 30 juta tanpa
transaksi => saldo 150 juta. Koreksi pembayaran Agustus +20 juta => buka ulang
September, bawaan menjadi 100 juta dan saldo 130 juta. Dashboard dan PDF harus
menunjukkan saldo terbaru 130 juta, bukan 230 juta.
