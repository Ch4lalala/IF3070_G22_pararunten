# Pararunten — IF3070 Dasar Inteligensi Artifisial

Dashboard penataan kendaraan pada geladak kapal, Kelompok 22.
Runner terminal mendukung Hill-Climbing with Sideways Move, Simulated Annealing, dan Genetic Algorithm.

## Menjalankan dashboard

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Buka alamat lokal yang ditampilkan terminal. Layar awal berisi initial state,
kontrol, dan final state. Laporan muncul setelah ada hasil; gulir ke bawah atau
klik **Lihat hasil**. Grafik kapal dan mobil menggunakan SVG.

## Tombol Mulai mengikuti Cakupan

Tidak ada lagi mode default satu percobaan:

- **HC:** sekali Mulai menjalankan **3 run**, dengan seed S, S+1, S+2.
- **GA:** sekali Mulai menjalankan **18 run**:
  - A: populasi kontrol tetap; 3 variasi generasi; 3 seed per konfigurasi = 9 run.
  - B: generasi kontrol tetap; 3 variasi populasi; 3 seed per konfigurasi = 9 run.
- Populasi dan generasi kontrol beserta tiga variasinya diatur di Pengaturan.
- Default GA: populasi kontrol 20, generasi kontrol 100, variasi generasi
  50/100/200, variasi populasi 10/20/40. Peluang mutasi dipertahankan 0.1.
- Variasi harus tepat tiga integer positif berbeda.
- Konfigurasi kontrol boleh muncul pada A dan B; keduanya tetap dicatat sebagai
  run terpisah sesuai dua kelompok eksperimen.
- Dataset tetap sama sepanjang satu sesi; randomisasi berasal dari seed.
- Tabel progres diperbarui setiap run selesai, bukan menunggu seluruh sesi.

**Generate Initial State** menaikkan seed satu angka dan menyembunyikan hasil aktif.
Mengubah pengaturan juga membersihkan tampilan aktif. Berkas hasil lama tetap ada
di Arsip. Klik Mulai lagi selalu membuat folder sesi baru, termasuk dari tampilan
arsip. Tombol Mulai tidak dinonaktifkan ketika membuka arsip.

HC pada medium/large bisa memerlukan waktu lama karena memeriksa seluruh tetangga
valid pada setiap langkah. Progres menampilkan run dan seed yang sedang diproses.

## Hasil yang disimpan dan ditampilkan

| Ketentuan Cakupan | Implementasi |
| --- | --- |
| State awal dan akhir | Gambar kapal, tabel state, dan seluruh state pada run.json |
| Objective akhir | Kartu hasil dan summary.csv |
| Grafik objective terhadap iterasi | Plot setiap run dan grafik gabungan tiga percobaan |
| Durasi pencarian | Kartu hasil, tabel, dan JSON |
| HC sideways: jumlah iterasi | Field iterations dan tabel ringkasan |
| HC sideways: maximum sideways move | Parameter max_sideways dan kartu parameter |
| GA: populasi dan banyak iterasi | Parameter aktual tiap run, bukan hanya kontrol |
| GA: maksimum dan rata-rata populasi per generasi | history.csv, grafik, dan JSON |
| GA: tiga variasi × tiga pengulangan per kelompok | Rencana eksperimen 9 run A + 9 run B |
| Analisis konsistensi | Minimum/rata-rata/maksimum, SD sampel, dan durasi per konfigurasi |
| Pengaruh parameter GA | Tabel dan grafik kelompok A/B |
| Perbandingan algoritma | Sesi lengkap HC/GA pada dataset sama dapat dibandingkan |

SA tersedia melalui main.py, termasuk tiga run, grafik PNG probabilitas, dan
frekuensi local optimum. Tampilan dashboard SA dikerjakan terpisah. Statistik restart tidak ditampilkan
karena varian HC yang digunakan adalah sideways move, bukan random restart.

## Eksperimen dan output tanpa dashboard

Menjalankan eksperimen dan membuat PNG tidak membutuhkan Streamlit atau Plotly.
Matplotlib diperlukan untuk membuat grafik melalui Agg, tanpa jendela aplikasi.

~~~bash
python -m pip install matplotlib
python main.py
~~~

Atur SHOW_PLOT di main.py untuk membuka jendela grafik. PNG tetap dibuat ketika SHOW_PLOT = False.

~~~text
main.py -> src/result_io.py -> output/
                                                     |
                                                     v
                                                  app.py
~~~

- main.py menjalankan algoritma dan mengatur tiga/18 percobaan.
- src/result_io.py membaca/menyimpan hasil dan membuat PNG tanpa dashboard.
- Setelah tombol Mulai selesai, dashboard membaca ulang hasil dari output.
- Menu Arsip membuka hasil main.py tanpa menjalankan algoritma kembali.

## Arsip permanen

Hasil baru disimpan berdasarkan algoritma:

~~~text
output/
  hill_climbing/
    hc_<waktu-sesi>/
      dataset.json             # Data kapal dan semua kendaraan
      session.json             # Parameter, rencana run, dan status sesi
      summary.csv              # Ringkasan tiga percobaan
      objective.png            # Tiga percobaan dalam satu grafik
      HC_seed-42/
        run.json               # State awal/akhir dan statistik
        history.csv            # Objective tiap iterasi
      HC_seed-43/
      HC_seed-44/
  genetic_algorithm/
    ga_<waktu-sesi>/            # Struktur serupa; 18 run kelompok A/B
  simulated_annealing/
    sa_<waktu-sesi>/            # Tiga run; objective.png dan probability.png
~~~

Data JSON/CSV dan plot per run disimpan setelah setiap percobaan. Grafik
gabungan dibuat setelah seluruh run selesai, kemudian status sesi menjadi complete. CSV dengan isi sama
tidak ditulis ulang ketika hanya status sesi yang berubah.

Jika proses terhenti, hasil run yang selesai tetap tersedia. Tidak ada hasil
buatan untuk run yang belum dijalankan. Gunakan menu Arsip untuk membukanya lagi.

Hasil run disimpan terpisah di output/hill_climbing/, output/simulated_annealing/, dan output/genetic_algorithm/. Menu Arsip saat ini mendukung hasil HC dan GA; tampilan SA ditambahkan kemudian.
Unduhan JSON lengkap dan CSV juga tersedia di dashboard.

## Interpretasi state dan nilai

- Objective hanya shipping fee kendaraan dimuat, dalam juta rupiah.
- ETA adalah metadata. Berat dan dimensi memakai unit dataset.
- Semua kendaraan tetap tercatat. None berarti tidak dimuat.
- Parkiran bawah kapal hanya tata letak visual, dengan skala terpisah.
- Warna kendaraan sama pada initial/final state. Sorot mobil untuk detail.
- HC: initial state dan final state pencarian.
- GA: gambar awal memakai individu terbaik populasi awal; gambar hasil memakai
  best_individual sepanjang pencarian, bukan selalu individu populasi terakhir.
  Pemilih setiap individu awal/akhir tersedia di laporan.
- Preview dan pencarian memakai fungsi, seed, urutan kendaraan, serta ukuran
  populasi sama sehingga populasi awal GA dapat direproduksi.
- Maksimum generasi GA boleh turun. Garis rekor terbaik tidak turun.
- History mencatat nilai sejak iterasi/generasi 0. Tidak ada animasi setiap state
  karena algoritma belum menyimpan snapshot state pada setiap langkah.
- Hitungan sideways HC berturut-turut direset setelah peningkatan objective;
  total_sideways menghitung seluruh langkah sideways.
- Durasi eksperimen baru HC, SA, dan GA mencakup inisialisasi dan pencarian.
  Jika initial state diberikan langsung ke HC/SA, duration_scope bernilai search_only.
  Penulisan arsip dan grafik tidak dimasukkan ke durasi algoritma.
- Perbandingan memakai snapshot dataset identik. Solusi terbaik yang ditemukan
  tidak otomatis membuktikan global optimum.

## Menjalankan algoritma dari main.py

Pengaturan menggunakan variabel di bagian atas main.py. Ubah nilainya, simpan
berkas, kemudian jalankan dari folder utama repository:

~~~bash
python main.py
~~~

Contoh pengaturan:

~~~python
ALGORITHM = "all"       # "hc", "sa", "ga", "all", atau "both"
DATASET = "medium"      # "small", "medium", atau "large"
SEEDS = [42, 43, 44]
SHOW_PLOT = False
~~~

- all menjalankan HC 3 kali, SA 3 kali, dan GA 18 kali: total 24 run.
- both menjalankan HC + GA.
- Untuk menjalankan SA saja, ubah ALGORITHM = "sa".
- Untuk memakai dataset small, ubah DATASET = "small".
- Dataset saat ini medium, mengikuti pengaturan terakhir pada kode.
- SEEDS harus memuat tepat tiga angka berbeda, minimal 0.
- Parameter algoritma menggunakan nilai bawaan di fungsi masing-masing.
- HC: max_sideways di src/algorithm/hill_climbing.py.
- SA: T0, alpha, T_min, dan max_iter di src/algorithm/simulated_annealing.py.
- GA: population_size, generations, dan mutation_rate di src/algorithm/genetic_algorithm.py.
- Fungsi get_default_parameters() di main.py membaca nilai bawaan fungsi algoritma.
- Untuk GA, default_variations() pada main.py menentukan tiga variasi:
  setengah nilai kontrol, nilai kontrol, dan dua kali nilai kontrol.
- Dengan default GA saat ini, generasi yang dicoba adalah 50/100/200 dan
  populasi yang dicoba adalah 10/20/40; setiap konfigurasi memakai tiga seed.
- SHOW_PLOT = True membuka jendela grafik setelah semua run selesai.
- PNG selalu dibuat dan disimpan, termasuk saat SHOW_PLOT = False.
- Pengaturan di bagian atas main.py memuat pilihan algoritma, dataset, seed, dan tampilan grafik.
  Parameter pencarian mengikuti fungsi algoritma; tidak memakai argumen terminal.

Setiap run langsung disimpan ke folder algoritmanya dalam output/.
Dataset medium/large dapat memerlukan waktu lebih lama, terutama pemeriksaan
tetangga. Durasi HC/SA/GA mencakup inisialisasi internal dan pencarian.
Durasi tidak mencakup penulisan berkas atau pembuatan grafik PNG.

## Plot setiap run dan grafik gabungan

Plot dibuat dari riwayat setiap percobaan. Sumbu horizontal menunjukkan iterasi
atau generasi dalam percobaan tersebut.

Di folder setiap seed/konfigurasi:
- HC: objective.png menampilkan objective terhadap iterasi.
- SA: objective.png dan probability.png menampilkan objective serta probabilitas
  penerimaan terhadap iterasi. Probabilitas memakai p=min(1, exp(delta/T)).
- GA: objective.png menampilkan maksimum objective dan rata-rata populasi.
- run.json dan history.csv menyimpan data lengkap; SA juga menyimpan probabilities.csv.

Selain plot per run, grafik perbandingan disimpan sejajar dengan summary.csv:
- HC: objective.png menggabungkan tiga percobaan.
- SA: objective.png dan probability.png masing-masing menggabungkan tiga percobaan.
- GA: objective_<kelompok>_pop-<P>_iter-<G>.png untuk setiap konfigurasi kelompok A/B.
  Dua panel menampilkan maksimum dan rata-rata populasi; masing-masing tiga kurva.
- Panjang kurva mengikuti jumlah iterasi aktual tiap run.
- Data tanpa kandidat pada SA ditampilkan sebagai celah pada kurva probabilitas.
- State akhir SA dan state terbaik tetap tersimpan terpisah pada run.json.

Contoh struktur HC:
~~~text
hc_<waktu>/
  summary.csv
  objective.png           # Gabungan tiga run
  HC_seed-42/
    run.json
    history.csv
    objective.png         # Hanya seed 42
  HC_seed-43/
  HC_seed-44/
~~~

Hasil tersimpan dapat dibuatkan plot kembali tanpa menjalankan ulang algoritma:
~~~python
from pathlib import Path
from src.result_io import load_session, save_plot

folder = Path("output/hill_climbing/hc_<waktu>")
session = load_session(folder)
for run in session["runs"]:
    save_plot([run], folder / run["run_id"])
save_plot(session["runs"], folder)
~~~

## Pengujian algoritma tanpa dashboard

Pengujian menggunakan unittest bawaan Python. Tidak memerlukan Streamlit,
Plotly, atau Matplotlib.

~~~bash
python -B -m unittest discover -s tests -v
~~~

Berkas tests/test_algorithms.py memeriksa:

- Validitas susunan dengan pemeriksaan sel grid terpisah dari validator program.
- Kecocokan objective, panjang history, durasi, dan pengulangan dengan seed sama.
- HC: tetangga valid, batas sideways, reset setelah peningkatan, dan penolakan nilai turun.
- SA: menerima/menolak nilai turun, probabilitas, suhu, alasan berhenti, dan hitungan local optimum.
- Pemeriksa local optimum dibandingkan dengan seluruh alternatif pada kasus kecil.
- GA: populasi, crossover/mutasi, roulette saat fitness nol, dan solusi terbaik sepanjang pencarian.
- Kasus kendaraan kosong, tidak muat, terlalu berat, dan parameter SA/GA tidak valid.
- HC dan SA pada small.json masing-masing memakai seed 42, 43, 44.
- GA memakai enam konfigurasi x tiga seed = 18 run singkat.

Parameter GA pada pengujian sengaja kecil: kontrol populasi 4, kontrol generasi 4,
variasi 2/4/6. HC memakai batas sideways 5 dan SA memakai 60 iterasi pada small.json.
Ini pengujian kebenaran program, bukan hasil eksperimen akhir untuk laporan.
Pengujian tidak membuka aplikasi, membuat grafik, atau menulis hasil run ke output.

## Struktur visualisasi

```text
app.py                         # Kontrol, kapal besar, dan progres langsung
main.py                        # Runner HC/SA/GA dan pengaturan percobaan
src/result_io.py               # Baca/simpan hasil dan pembuatan PNG
src/visualization/
  ship_scene.py                # Kapal, mobil, dan parkiran SVG
  reports.py                   # Laporan sesuai algoritma dan analisis eksperimen
  charts.py                    # Grafik Plotly
  style.css                    # Tata letak
.streamlit/config.toml         # Tema dan server lokal
requirements.txt               # Dependensi Python
```

