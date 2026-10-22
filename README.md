# Pararunten - IF3070 Dasar Inteligensi Artifisial

## Deskripsi Repository

Repository Tugas Besar IF3070 Kelompok 22 berisi program untuk menentukan kendaraan yang dimuat beserta posisi dan orientasinya pada geladak kapal. Program memaksimalkan total **ShippingFee** dengan memenuhi batas geladak, larangan kendaraan bertumpuk, dan kapasitas berat kapal.

Algoritma yang digunakan:

- Hill-Climbing with Sideways Move.
- Simulated Annealing.
- Genetic Algorithm.

Implementasi algoritma menggunakan **Python**, sedangkan visualisasi menggunakan **Streamlit** dan **Plotly**. Grafik hasil eksperimen disimpan menggunakan **Matplotlib**.

## Setup

Gunakan **Python 3.10 atau lebih baru**. Perintah berikut mengambil branch pengembangan `daniel`:

```bash
git clone --branch daniel https://github.com/Ch4lalala/IF3070_G22_pararunten.git
cd IF3070_G22_pararunten
python -m pip install -r requirements.txt
```

Jika repository sudah tersedia secara lokal, masuk ke folder repository dan jalankan perintah instalasi dependensi tersebut.

## Menjalankan Program

### Melalui Web

```bash
python -m streamlit run app.py
```

Buka alamat lokal yang ditampilkan terminal, biasanya `http://localhost:8501`.

1. Pilih algoritma dan atur dataset melalui **Pengaturan**.
2. Klik **Generate Initial State** jika ingin membuat susunan awal baru.
3. Klik **Mulai** untuk menjalankan eksperimen.
4. Gulir ke panel hasil untuk melihat ringkasan percobaan dan grafik. Pilih percobaan untuk melihat state awal dan hasilnya.

HC dan SA masing-masing dijalankan **3 kali**. GA dijalankan **18 kali**: tiga variasi generasi dengan populasi tetap dan tiga variasi populasi dengan generasi tetap, masing-masing diulang tiga kali. Hasil tersimpan dapat dibuka kembali melalui menu **Arsip**.

### Melalui Terminal

```bash
python main.py
```

Pengaturan berada di bagian atas `main.py`:

| Variabel | Keterangan |
| --- | --- |
| `ALGORITHM` | Pilih `"hc"`, `"sa"`, `"ga"`, atau `"all"` untuk menjalankan ketiganya. |
| `DATASET` | Pilih `"small"`, `"medium"`, atau `"large"`. |
| `SEEDS` | Tiga seed berbeda untuk pengulangan eksperimen. |
| `SHOW_PLOT` | `True` untuk membuka jendela grafik setelah eksperimen selesai. |

### Penyimpanan Hasil

Hasil dari web maupun terminal otomatis disimpan di:

```text
output/
|-- hill_climbing/
|-- simulated_annealing/
`-- genetic_algorithm/
```

Setiap sesi menyimpan dataset, status sesi, ringkasan CSV, serta hasil setiap percobaan berupa JSON, riwayat objective, dan grafik PNG. Grafik tetap disimpan meskipun `SHOW_PLOT = False`.

## Pembagian Tugas Anggota Kelompok

| Nama | NIM | Tugas |
| --- | --- | --- |
| Ahmad Aditya Ar Rasyid | 18224023 | Pembuatan baseline untuk semua algoritma.<br>Pembuatan algoritma Genetic Algorithm.<br>Menyusun laporan. |
| Daniel Benaya Toar Supaath | 18224027 | Pembuatan visualisasi.<br>Pembuatan algoritma Hill-Climbing with Sideways Move.<br>Menyusun laporan. |
| Ahmad Rizal Fahmi | 18224085 | Pembuatan algoritma Simulated Annealing.<br>Menyusun laporan. |
