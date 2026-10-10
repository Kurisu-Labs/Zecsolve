Shielded Payment Exception Engine
Riset produk, arsitektur sistem, rich picture, dan execution plan untuk Colosseum Crypto World’s Fair 2026 · 10 Oktober 2026
Saya menyarankan membangun payment operations layer untuk Zcash, bukan payment gateway, escrow, atau audit tool baru.
Konsep utamanya:
Resolve shielded payment exceptions without compromising financial privacy.

Ketika pembayaran ZEC tidak cocok dengan invoice, terlambat, kurang bayar, atau diklaim berkali-kali, aplikasi membantu merchant menyelidiki masalah tersebut, menerima bukti dari customer, dan menghasilkan keputusan yang dapat diperiksa ulang.
Sistem tidak memegang dana, tidak meminta spending key, dan tidak menganggap setiap klaim pembayaran sebagai fakta.
1. Hasil riset: seberapa besar gap-nya?
Saya menemukan empat kompetitor atau solusi berdekatan yang relevan.
Existing solution	Yang sudah diselesaikan	Celah yang bisa diuji
CipherPay	Checkout, invoice, monitoring, webhook, refund API	Case management dan investigasi exception lintas provider
Zink	Payment links dan invoice reconciliation	Partial/overpayment serta refunds belum diimplementasikan
Glasspane	Selective receipt, verification, tamper detection, audit packet	Menggunakan verified evidence untuk menyelesaikan konflik invoice
ZecLedger	View-only accounting, partial-match flag, pelaporan	Collaborative investigation dan case workflow


GitHub
+3


Ada satu preseden yang sangat penting: shielded.bid sudah mendokumentasikan penanganan duplicate evidence, conflicting settlement, amount mismatch, dan manual refund review di atas CipherPay. Jadi, exception handling sudah terbukti sebagai kebutuhan operasional setidaknya pada satu implementasi, tetapi itu belum membuktikan adanya pasar yang besar untuk produk independen. 

shielded.bid



Gap yang kita incar
Bukan membuat kemampuan mendeteksi underpayment yang belum pernah ada.
Melainkan membangun workflow reusable yang memungkinkan merchant mengubah masalah pembayaran menjadi case, mengumpulkan evidence, mengevaluasi klaim, dan mencatat keputusan yang bisa dipertanggungjawabkan.
Diferensiasi harus dibuktikan pada tiga kemampuan:
- Evidence-aware investigation: Sistem membedakan informasi dari processor, klaim customer, dan bukti kriptografis.
- Deterministic exception handling: Setiap jenis exception memiliki aturan evaluasi dan alasan yang bisa direproduksi.
- Portable resolution record: Keputusan merchant dapat diekspor bersama bukti dan riwayatnya, tanpa membagikan viewing key.
Ini masih merupakan kandidat product gap, bukan pasar yang sudah tervalidasi.
2. Product definition
Working concept
Shielded Payment Exception Engine
Category: Zcash payment operations infrastructure
Primary customer: Merchant atau crypto-native business yang menerima shielded ZEC.
Secondary customer: Payment processor dan platform yang ingin mengotomatisasi payment support.
Core workflow: Detect → Investigate → Verify → Resolve → Export.
Non-goals: Bukan escrow, bukan wallet, bukan payment gateway, dan bukan sistem yang otomatis mengirim refund.

Exception yang akan ditangani
Exception	Kondisi	Respons sistem
Underpayment	Jumlah terverifikasi lebih kecil dari invoice	Hitung kekurangan, minta top-up atau review
Duplicate claim	Output pembayaran yang sama diklaim untuk dua invoice	Tolak double-credit, tandai konflik
Tampered evidence	Receipt tidak lolos verifikasi kriptografis	Tolak evidence, tampilkan alasan
Missing/wrong memo	Referensi tidak cocok atau tidak tersedia	Minta bukti tambahan; jangan auto-match
Late payment	Pembayaran terjadi setelah masa berlaku invoice	Buka review, bukan otomatis mengabaikannya
Overpayment	Jumlah melebihi invoice	Hitung selisih dan sarankan review/refund
Untuk submission, saya merekomendasikan tiga exception pertama sebagai P0. Missing memo, late payment, dan overpayment menjadi P1.
Hal terpenting: jangan gabungkan tiga jenis kebenaran
Sistem harus memisahkan:
Lapisan	Yang benar-benar diketahui
Payment observation	Payment processor atau scanner melaporkan transaksi tertentu
Cryptographic verification	Receipt berhasil membuka output tertentu yang cocok dengan transaksi
Business resolution	Merchant memutuskan bagaimana output itu diperhitungkan terhadap invoice
Sebuah receipt yang valid tidak otomatis membuktikan identitas pembayar, bahwa invoice telah lunas, atau bahwa merchant sudah menyetujui penyelesaian.
ZIP-311 masih berstatus Draft, sementara implementasi Glasspane memakai per-output Out Cipher Key untuk membuka recipient, amount, dan memo dari output Orchard/Sapling tertentu. Ini cocok sebagai dasar POC, tetapi bukan bukti kepemilikan identitas customer. 

zips.z.cash
+1



3. Scope untuk hackathon
Karena Colosseum menetapkan deadline 12 Oktober 2026 pukul 23.59 Pacific Time, batasnya setara dengan 13 Oktober pukul 13.59 WIB. Seluruh anggota tim juga perlu terdaftar sebelum deadline. 

colosseum.com



Saya tidak akan mencoba membuat seluruh payment infrastructure dalam waktu tersisa.
Komponen	MVP sekarang	Setelah hackathon
Invoice input	Manual/import	CipherPay API sync
Case management	Create, inspect, resolve	Collaboration, notifications
Zcash verification	Existing Orchard receipts	Ironwood support
Exception engine	3 deterministic rules	Extended policy engine
Payment monitoring	Imported observations	Live processor adapter
Audit trail	Append-only events	Signed attestations and external anchoring
Export	JSON evidence report	Accounting integrations
Refunds	Record decision only	Wallet-assisted refund workflow
Kompromi teknis yang harus jujur disampaikan: Glasspane mendokumentasikan parser transaksi sampai NU6.2. Jadi receipt fixtures Orchard historis dapat dipakai untuk membuktikan engine bekerja dengan transaksi mainnet sungguhan, tetapi belum membuktikan kompatibilitas dengan pembayaran Ironwood yang baru. 

GitHub



Ini lebih baik daripada membuat demo seolah-olah mendukung seluruh Zcash mainnet saat ini padahal verifier belum kompatibel.
4. Arsitektur sistem
Saya merekomendasikan modular monolith untuk hackathon, bukan microservices.
Frontend mengelola case dan evidence. FastAPI mengelola business rules serta audit history. Rust menjalankan verifikasi Zcash. Semua bisa dioperasikan dengan satu backend deployment pada awalnya.
#chatgpt-mermaid-_r_de_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_de_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_de_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_de_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-_r_de_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_de_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_de_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_de_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_de_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_de_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_de_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_de_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_de_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_de_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_de_ p{margin:0;}#chatgpt-mermaid-_r_de_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_de_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_de_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_de_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_de_ .label text,#chatgpt-mermaid-_r_de_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_de_ .node rect,#chatgpt-mermaid-_r_de_ .node circle,#chatgpt-mermaid-_r_de_ .node ellipse,#chatgpt-mermaid-_r_de_ .node polygon,#chatgpt-mermaid-_r_de_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-_r_de_ .rough-node .label text,#chatgpt-mermaid-_r_de_ .node .label text,#chatgpt-mermaid-_r_de_ .image-shape .label,#chatgpt-mermaid-_r_de_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_de_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_de_ .rough-node .label,#chatgpt-mermaid-_r_de_ .node .label,#chatgpt-mermaid-_r_de_ .image-shape .label,#chatgpt-mermaid-_r_de_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_de_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_de_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_de_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-_r_de_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-_r_de_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-_r_de_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_de_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_de_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_de_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-_r_de_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-_r_de_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_de_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_de_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_de_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_de_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_de_ .icon-shape,#chatgpt-mermaid-_r_de_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_de_ .icon-shape p,#chatgpt-mermaid-_r_de_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-_r_de_ .icon-shape .label rect,#chatgpt-mermaid-_r_de_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_de_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_de_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_de_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_de_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_de_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_de_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_de_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_de_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_de_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_de_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_de_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_de_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-_r_de_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_de_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_de_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_de_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_de_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_de_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_de_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_de_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_de_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_de_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_de_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_de_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-_r_de_ .node rect,#chatgpt-mermaid-_r_de_ .node circle,#chatgpt-mermaid-_r_de_ .node ellipse,#chatgpt-mermaid-_r_de_ .node polygon,#chatgpt-mermaid-_r_de_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_de_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_de_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2px,2px;}#chatgpt-mermaid-_r_de_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_de_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_de_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Zcash VerificationBackend — FastAPIFrontend — Vue 3Rust / Glasspane verifierZcash transaction dataCases and Evidence APIDeterministic Rules EngineResolution and Audit LogPayment Provider AdapterMerchant dashboardCustomer evidencesubmissionReviewer portalPostgreSQLCipherPay or other provider





Arsitektur target. Payment-provider integration dapat ditunda apabila akses API belum tersedia.Technology decisions
Component	Stack	Alasan
Web application	Vue 3, TypeScript, Tailwind	Dashboard dan evidence submission
Backend	FastAPI + Pydantic	Cepat untuk CRUD, validation, workflow
Database	PostgreSQL	Relational cases, invoice, events, constraints
Cryptographic verifier	Rust + Glasspane components	Reuse verified receipt implementation
Blockchain data	Raw transaction fixtures, kemudian lightwalletd/compatible reader	Memisahkan pembuktian output dan observasi konfirmasi
Export	JSON + SHA-256	Reproducible evidence package
Deployment	Vercel + Docker backend	Cepat untuk hackathon
Untuk percepatan, backend FastAPI dan Rust verifier bisa berada dalam satu Docker container. FastAPI memanggil binary Rust dengan input yang divalidasi, batas ukuran file, dan timeout. Setelah hackathon, verifier bisa dipindah ke worker terpisah.
Poin penting: Jangan mengharuskan merchant memasukkan viewing key ke aplikasi ini. Untuk MVP, data pembayaran berasal dari receipt atau payment observation yang memang diserahkan secara eksplisit. Gateway yang sudah ada tetap menangani scanning dan checkout.
Data model inti
#chatgpt-mermaid-_r_dn_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_dn_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_dn_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_dn_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-_r_dn_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_dn_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_dn_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_dn_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_dn_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_dn_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_dn_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_dn_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_dn_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_dn_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_dn_ p{margin:0;}#chatgpt-mermaid-_r_dn_ .entityBox{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_dn_ .relationshipLabelBox{fill:rgb(48, 48, 48);opacity:0.7;background-color:rgb(48, 48, 48);}#chatgpt-mermaid-_r_dn_ .relationshipLabelBox rect{opacity:0.5;}#chatgpt-mermaid-_r_dn_ .labelBkg{background-color:rgba(48, 48, 48, 0.5);}#chatgpt-mermaid-_r_dn_ .edgeLabel{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_dn_ .edgeLabel .label rect{fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_dn_ .edgeLabel .label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_dn_ .edgeLabel .label{fill:rgb(31, 78, 148);font-size:14px;}#chatgpt-mermaid-_r_dn_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_dn_ .edge-pattern-dashed{stroke-dasharray:8,8;}#chatgpt-mermaid-_r_dn_ .node rect,#chatgpt-mermaid-_r_dn_ .node circle,#chatgpt-mermaid-_r_dn_ .node ellipse,#chatgpt-mermaid-_r_dn_ .node polygon{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-_r_dn_ .relationshipLine{stroke:rgb(175, 175, 175);stroke-width:1px;fill:none;}#chatgpt-mermaid-_r_dn_ .marker{fill:none!important;stroke:rgb(175, 175, 175)!important;stroke-width:1;}#chatgpt-mermaid-_r_dn_ [data-look=neo].labelBkg{background-color:rgba(48, 48, 48, 0.5);}#chatgpt-mermaid-_r_dn_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_dn_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_dn_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_dn_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_dn_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_dn_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_dn_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_dn_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_dn_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_dn_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-_r_dn_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_dn_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_dn_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_dn_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_dn_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_dn_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_dn_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_dn_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}INVOICEuuididPKbigintexpected_zatoshisstringrecipientstringmemo_referencestringsnapshot_hashEXCEPTION_CASEuuididPKuuidinvoice_idFKstringcategorystringstateCLAIMuuididPKuuidcase_idFKstringreported_txidEVIDENCEuuididPKuuidcase_idFKstringevidence_typestringcontent_hashVERIFICATIONuuididPKuuidevidence_idFKstringreceipt_statusstringchain_statusstringmatch_statusCASE_EVENTuuididPKstringactionstringevent_hashRESOLUTIONuuididPKstringoutcomestringapproved_byOUTPUT_ALLOCATIONstringoutput_idPKuuidinvoice_idFKstringcredit_statehasreceivescontainschecked_byrecordsconcludescredits





Ada beberapa keputusan desain penting:
Gunakan zatoshis sebagai integer. Jangan memakai floating point untuk nilai pembayaran. Satu ZEC memiliki 100 juta zatoshis.
Identifikasi output, bukan sekadar transaksi. Kunci yang saya sarankan adalah network:pool:txid:output_index, sebab satu transaksi dapat mengandung beberapa shielded outputs.
Pisahkan case status dan proof status. Sebuah case bisa masih UNDER_REVIEW walaupun satu receipt sudah valid.
Jangan membuat audit log yang mengklaim tidak dapat dimodifikasi. Untuk MVP, buat append-only event history dan integritas berbasis hash. Signature atau external anchoring dapat ditambahkan kemudian jika membutuhkan jaminan lebih kuat.
5. Business logic: bagaimana exception diputuskan?
#chatgpt-mermaid-_r_e0_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_e0_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_e0_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_e0_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-_r_e0_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_e0_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_e0_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_e0_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_e0_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_e0_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_e0_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_e0_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_e0_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_e0_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_e0_ p{margin:0;}#chatgpt-mermaid-_r_e0_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_e0_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_e0_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_e0_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_e0_ .label text,#chatgpt-mermaid-_r_e0_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_e0_ .node rect,#chatgpt-mermaid-_r_e0_ .node circle,#chatgpt-mermaid-_r_e0_ .node ellipse,#chatgpt-mermaid-_r_e0_ .node polygon,#chatgpt-mermaid-_r_e0_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-_r_e0_ .rough-node .label text,#chatgpt-mermaid-_r_e0_ .node .label text,#chatgpt-mermaid-_r_e0_ .image-shape .label,#chatgpt-mermaid-_r_e0_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_e0_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_e0_ .rough-node .label,#chatgpt-mermaid-_r_e0_ .node .label,#chatgpt-mermaid-_r_e0_ .image-shape .label,#chatgpt-mermaid-_r_e0_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_e0_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_e0_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_e0_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-_r_e0_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-_r_e0_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-_r_e0_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_e0_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_e0_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_e0_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-_r_e0_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-_r_e0_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_e0_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_e0_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_e0_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_e0_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_e0_ .icon-shape,#chatgpt-mermaid-_r_e0_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_e0_ .icon-shape p,#chatgpt-mermaid-_r_e0_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-_r_e0_ .icon-shape .label rect,#chatgpt-mermaid-_r_e0_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_e0_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_e0_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_e0_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_e0_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_e0_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_e0_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_e0_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_e0_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_e0_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_e0_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_e0_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_e0_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-_r_e0_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_e0_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_e0_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_e0_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_e0_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_e0_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_e0_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_e0_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_e0_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_e0_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_e0_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_e0_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-_r_e0_ .node rect,#chatgpt-mermaid-_r_e0_ .node circle,#chatgpt-mermaid-_r_e0_ .node ellipse,#chatgpt-mermaid-_r_e0_ .node polygon,#chatgpt-mermaid-_r_e0_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_e0_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_e0_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2px,2px;}#chatgpt-mermaid-_r_e0_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_e0_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_e0_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI","Helvetica","Apple Color Emoji","Arial",sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}Customer submits a paymentclaimReceipt available?Await evidence / manualreviewVerify receipt andtransactionReceipt valid?Invalid evidence: showreasonChain status confirmed?Chain evidence unavailableOutput already credited?Duplicate claim conflictRecipient and referencematch?Manual matching reviewAmount meets invoice?Underpayment /overpaymentEligible for creditMerchant approvesresolutionNoYesNoYesUnknownYesYesNoNoYesNoYes





Hasil verifikasi harus deterministic, reproducible, dan explainable, bukan AI yang menebak apakah transaksi valid.
Misalnya:
Exception CASE-018
Underpayment

Invoice expected
0.002 ZEC


Verified output amount
0.001 ZEC




Shortfall
0.001 ZEC

Receipt verification
 Valid

Business resolution
Awaiting merchant

Suggested action: request an additional payment for the shortfall or manually review the invoice. The application has not sent a refund or moved funds.


Contoh menggunakan invoice sintetis untuk menunjukkan hasil classification. Bukan transaksi baru yang benar-benar dilakukan oleh aplikasi.6. Threat model dan security requirements
Risiko	Mitigasi
Fake payment confirmation	Verify webhook signature, timestamp, dan provenance
Reuse bukti pembayaran	Unique output identifier + database constraint
Receipt dimodifikasi	Cryptographic verification against raw transaction
Invoice dimodifikasi	Immutable invoice snapshot dan version hash
Data pelanggan bocor	Scoped access, minimal disclosure, private storage
Blockchain data tidak tersedia	Status UNAVAILABLE, bukan INVALID
Reviewer meminta viewing key	Reviewer hanya menerima case-scoped evidence
Merchant membuat keputusan keliru	Human approval, alasan keputusan, audit history
Satu batas keamanan yang tidak boleh terlewat: receipt yang sudah dibagikan dapat diteruskan dan diverifikasi ulang oleh siapa pun yang mendapatkannya. Jadi disclosure memang terbatas pada output yang dipilih, tetapi tidak dapat ditarik kembali secara kriptografis setelah bocor. 

GitHub



7. Execution plan sampai deadline
10
OCT
Foundation + Zcash POC
Hari ini
Setup repository, arsitektur monolith, skema database, dan eksperimen Rust verifier. Targetnya: satu mainnet Orchard receipt valid berhasil diverifikasi dan receipt yang dimodifikasi ditolak.
 Exit criterion: crypto verification berjalan secara reproducible.



11
OCT
Core product + integration
Implementasi case management, rules engine, output deduplication, evidence upload, merchant dashboard, dan reviewer report.
 Exit criterion: tiga kasus P0 bisa diselesaikan dari UI.



12
OCT
Polish, user validation, dan submission
Deployment, failure-path testing, evidence export, README, product narrative, presentasi, dan demo recording. Hubungi pengguna atau pengembang payment processor untuk validasi kebutuhan.
 Exit criterion: live demo stabil dan submission selesai dengan buffer.



13
OCT
Submission contingency — sebelum 13.59 WIB
Gunakan hanya untuk verifikasi submission dan perbaikan kritis. Jangan menunda pengiriman sampai menit terakhir.



Acceptance tests wajib
MVP readiness checklist
0/8 complete



[ ] Valid Orchard receipt berhasil membuka output transaksi mainnet yang benar.
[ ] Tampered OCK atau output index gagal diverifikasi.
[ ] Verified payment dengan jumlah kurang menghasilkan UNDERPAID.
[ ] Output yang sama tidak bisa mengkredit dua invoice.
[ ] Missing receipt tidak dianggap sebagai invalid payment.
[ ] Reviewer dapat melihat alasan dan provenance setiap keputusan.
[ ] Tidak ada seed, spending key, atau viewing key di log dan export.
[ ] Deployment dan demo dapat diulang dari clean environment.

8. Business model dan go-to-market
Saya akan menguji model B2B payment-operations SaaS dengan kemungkinan monetisasi subscription atau usage-based per investigated case.
Namun, ada tiga hipotesis yang perlu divalidasi:
Hipotesis	Cara menguji
Merchant cukup sering mengalami exception	Wawancara dengan merchant ZEC atau payment operators
Investigasi manual menyita waktu	Bandingkan waktu penyelesaian sebelum/sesudah tool
Integrasi pihak ketiga lebih menarik daripada fitur gateway	Tanyakan kepada developer payment processor
Target awal bukan mengklaim punya puluhan ribu merchant, melainkan mendapatkan beberapa percakapan yang membuktikan atau membantah masalah tersebut.
Untuk pitch Colosseum, fokus pada kemampuan yang belum ditawarkan secara menyeluruh sebagai reusable workflow, bukan mengklaim kita menemukan payment dispute pertama.
9. Rencana demo untuk juri
Demo story — target 3 menit
Proposed sequence

0:00–0:25	Masalah: pembayaran privat bermasalah tidak bisa diselesaikan hanya dengan block explorer.
0:25–1:05	Buka invoice dan perlihatkan underpayment menggunakan verified historical receipt.
1:05–1:45	Klaim output yang sama pada invoice lain; sistem menolak double-credit.
1:45–2:20	Unggah tampered receipt; verifier menunjukkan kegagalan.
2:20–3:00	Tampilkan resolution history dan export case report.

Colosseum juga meminta video presentasi sekitar 2–3 menit terpisah dari product demo yang maksimal tiga menit, beserta GitHub, product positioning, dan go-to-market. Aturan resminya mewajibkan materi submission berbahasa Inggris. 

Colosseum
+1



10. Blueprint siap untuk development
Saya sudah siapkan dokumen Markdown berbahasa Inggris yang bisa langsung digunakan sebagai handoff ke tim atau Codex. Isinya mencakup scope P0/P1, arsitektur Mermaid, data model, endpoint API, rules engine, threat model, test scenarios, sprint plan, business hypothesis, serta referensi kompetitor.

Project Blueprint — Markdown
201 lines · English · Editable architecture source


 Open project blueprintDownload Markdown blueprint

Final direction
Saya akan mempertahankan satu positioning:
Shielded Payment Exception Engine — the resolution layer for private payments.
Nilai jual awalnya bukan sekadar mendeteksi bahwa pembayaran kurang, tetapi menghasilkan keputusan yang jelas tentang apa yang diketahui, bukti apa yang masih kurang, dan tindakan apa yang boleh dilakukan merchant.
Dengan waktu pengerjaan yang pendek, prioritas tertinggi adalah verified evidence + deterministic exception rules + usable case workflow. Itu cukup untuk menunjukkan satu technical contribution yang nyata sekaligus arah bisnis yang bisa dilanjutkan setelah hackathon.
Terkait permintaan melupakan nama-nama sebelumnya, saya akan tetap menghindari penggunaannya. Untuk penghapusan penuh dari Memory, pengguna perlu memperbarui Memory summary melalui Settings → Personalization dan menghapus chat asal serta sumber lain yang memuat informasi tersebut.
