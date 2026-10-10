beberapa aturan perlu diperjelas sebelum coding:
1. Underpayment harus memakai total pembayaran yang sudah dialokasikan.
   Invoice 0,01 ZEC yang memiliki dua pembayaran valid sebesar 0,006 dan 0,004 sudah mencukupi. Jangan membandingkan setiap receipt secara terpisah dengan seluruh tagihan.
2. Pengiriman ulang bukan selalu duplicate claim bermasalah.
   Receipt yang sama untuk invoice yang sama harus mengembalikan hasil sebelumnya tanpa menambah kredit. Konflik terjadi ketika output yang sama hendak dialokasikan ke invoice berbeda. Batasan database harus bekerja saat permintaan datang bersamaan.
3. Pisahkan INVALID, UNSUPPORTED, dan UNAVAILABLE.
   Bukti gagal pemeriksaan, format belum didukung, dan sumber blockchain tidak tersedia adalah tiga kondisi berbeda. “Tidak ditemukan” juga belum cukup untuk menyebut receipt telah dimanipulasi.
4. Tentukan isi paket yang bisa diperiksa ulang.
   Ekspor perlu mencakup snapshot invoice, receipt, transaksi yang diperiksa, sumber/status blockchain saat pemeriksaan, versi verifier dan aturan, serta keputusan merchant. SHA-256 saja tidak membuktikan siapa yang membuat laporan atau bahwa keputusan bisnisnya benar.
5. Lengkapi akses merchant dan reviewer.
   Setiap kasus harus terikat ke merchant, dengan hak akses evidence yang jelas. Receipt tetap membuka jumlah, penerima, dan memo pembayaran terpilih; receipt juga bisa diteruskan setelah dibagikan. Batas pengungkapan Glasspane.
Ada pula bagian dokumen yang masih berupa placeholder: “Acceptance tests … complete” tidak disertai daftar hasil pengujian, dan tautan blueprint belum menyertakan isi berkasnya. Jadi ini rencana yang lebih konkret, belum bukti implementasi selesai.
Untuk mulai, ambil satu potongan dari blueprint ini: satu invoice sintetis + satu receipt historis nyata → verifier → pencocokan → alokasi database → laporan alasan. Setelah berhasil, uji pengiriman ulang, konflik invoice, dan receipt tampered. Pilihan framework bisa mengikuti kemampuan tim; ketergantungan terpenting tetap verifier yang benar-benar berjalan.
