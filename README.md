# FRAUD DETECTION ANALYSIS SYSTEM (FDAS)

Sistem Analisis Deteksi Fraud mutasi rekening menggunakan Hybrid Model LightGBM & LSTM dengan Explainable AI (SHAP).

## 📋 Prasyarat Sistem

Sebelum menjalankan aplikasi, pastikan laptop Anda sudah terinstall:

1. **Python 3.9 atau versi lebih baru**
   - Download di [python.org](https://www.python.org/downloads/)
2. **Microsoft C++ Build Tools** (Diperlukan oleh library `lightgbm` dan `shap`)
   - Download di [visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
3. **Database (Opsional)**
   - Secara default, aplikasi menggunakan **SQLite** (file `.db` lokal) agar mudah dijalankan tanpa setup database.
   - Jika ingin menggunakan **MySQL**, install XAMPP atau MySQL Server.

## 🚀 Cara Menjalankan di Laptop

Ikuti langkah-langkah berikut secara berurutan:

### 1. Persiapkan Folder Project
Extract file project FDAS ke sebuah folder (misal: `C:\fdas`).

### 2. Buka Terminal / Command Prompt
Buka terminal dan masuk ke folder project tersebut:
```bash
cd path/to/your/folder/fdas
```

### 3. Buat Virtual Environment (Sangat Direkomendasikan)
Agar library tidak berantakan dengan library Python lainnya:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Library / Dependency
Gunakan file `requirements.txt` yang sudah disediakan:
```bash
pip install -r requirements.txt
```

### 5. Jalankan Aplikasi
Jalankan perintah streamlit:
```bash
streamlit run app.py
```

Setelah itu, aplikasi akan terbuka secara otomatis di browser Anda pada alamat `http://localhost:8501`.

---

## 🛠️ Konfigurasi Database MySQL (Opsional)

Jika ingin beralih dari SQLite ke MySQL:
1. Buat database di MySQL dengan nama `fdas_db`.
2. Edit file `.env` atau set environment variable berikut:
   - `USE_MYSQL=true`
   - `MYSQL_HOST=localhost`
   - `MYSQL_USER=root`
   - `MYSQL_PASSWORD=`
   - `MYSQL_DATABASE=fdas_db`

## 📁 Struktur Folder Utama

- `app.py`: File utama aplikasi Streamlit.
- `modules/`: Engine utama (Cleansing, LightGBM, LSTM, XAI, Report).
- `database/`: Konfigurasi dan inisialisasi database.
- `models/`: Tempat penyimpanan model yang sudah ditraining (`.pkl` dan `.h5`).
- `uploads/`: Folder file yang diupload.
- `cleaned/`: Folder dataset hasil cleansing.
- `reports/`: Folder hasil export PDF report.

## 👤 Akun Demo
Karena sistem menggunakan enkripsi password, silakan pilih menu **"Create Account"** pada halaman login saat pertama kali menjalankan aplikasi untuk membuat akun user baru.

---
**Catatan Keamanan:** 
Aplikasi ini menggunakan model Machine Learning yang dilatih secara realtime jika model belum ada di folder `models/`. Gunakan file `REK 1.xlsx` sebagai contoh input mutasi rekening.
