# Dokumentasi Fungsi Menu FDAS (Fraud Detection Analysis System)

Sistem ini dirancang dengan estetika *Cyber Intelligence* dan *Forensic Fintech* untuk mendukung deteksi fraud perbankan yang canggih. Berikut adalah penjelasan fungsi dari masing-masing menu yang terdapat pada sidebar **Core Systems**:

---

### 1. Dashboard (Intelligence Hub)
- **Fungsi Utama**: Memberikan gambaran visual instan mengenai kondisi keamanan sistem.
- **Fitur**: 
    - Menampilkan KPI utama: Total Transaksi, Kasus Fraud, Akurasi Hybrid, dan Status Kesehatan Sistem.
    - Grafik perbandingan performa model (LightGBM vs LSTM vs Hybrid).
    - Indikator stabilitas sistem dan daftar peringatan forensik terbaru.

### 2. Cleansing (Data Preparation)
- **Fungsi Utama**: Tahap awal pemrosesan data (Preprocessing).
- **Fitur**:
    - Unggah dataset transaksi mentah (Format Excel).
    - Menjalankan algoritma pembersihan data (Cleansing) untuk menangani nilai yang hilang (missing values) atau format yang tidak konsisten.
    - Menampilkan cuplikan data hasil pembersihan sebelum dianalisis.

### 3. Analisis (Forensic Decision Support System)
- **Fungsi Utama**: Mesin inti pendeteksi fraud menggunakan kecerdasan buatan.
- **Fitur**:
    - Menjalankan mesin Hybrid AI (LightGBM + LSTM).
    - Memberikan skor risiko (*Risk Scoring*) untuk setiap rekening/transaksi.
    - **Explainable AI (XAI)**: Memberikan penjelasan mengapa sebuah transaksi dianggap fraud melalui logika SHAP.
    - Rekomendasi operasional untuk investigator.

### 4. Transaction Dictionary (Knowledge Base)
- **Fungsi Utama**: Pusat informasi dan referensi data.
- **Fitur**:
    - Referensi istilah teknis perbankan yang digunakan dalam dataset.
    - Membantu investigator memahami arti dari setiap kolom data yang sedang diinvestigasi.

### 5. Fraud Rules (Operational Logic)
- **Fungsi Utama**: Pengaturan logika bisnis dan ambang batas risiko.
- **Fitur**:
    - Konfigurasi nilai ambang batas (*threshold*) untuk kategori: Normal, High Risk, dan Fraud.
    - Memungkinkan sistem untuk tetap fleksibel terhadap perubahan pola fraud di lapangan.

### 6. Evaluation Dashboard (Methodology Validation)
- **Fungsi Utama**: Panel validasi ilmiah untuk keperluan akademis (Tesis).
- **Fitur**:
    - Menampilkan metriks evaluasi mendalam: *Confusion Matrix, Precision-Recall Curve, dan ROC-AUC*.
    - Perbandingan stabilitas model terhadap gangguan (*Adversarial Noise*).

### 7. History Analysis (Forensic Records)
- **Fungsi Utama**: Basis data historis hasil deteksi.
- **Fitur**:
    - Melihat kembali hasil analisis yang telah dilakukan di masa lalu.
    - Analisis tren kejadian fraud berdasarkan data historis.

### 8. Investigation Log (Audit Trail)
- **Fungsi Utama**: Dokumentasi tindakan investigator.
- **Fitur**:
    - Pencatatan catatan manual oleh petugas investigasi.
    - Berguna sebagai bukti audit (*Audit Trail*) untuk setiap keputusan yang diambil terhadap rekening yang mencurigakan.

### 9. User Settings (System Configuration)
- **Fungsi Utama**: Pengaturan akun dan informasi teknis.
- **Fitur**:
    - Profil pengguna yang masuk (investigator).
    - Informasi status koneksi database (SQLite/MySQL).
    - Pengaturan tema dan preferensi sistem lainnya.

---
*Dokumentasi ini dibuat untuk mendukung implementasi sistem FDAS pada lingkungan perbankan Profesional.*
