# Hasil eksperimen

Hasil dibuat otomatis oleh main.py atau tombol Mulai di dashboard.

~~~bash
python main.py
~~~

Pilih algoritma dan dataset melalui bagian PENGATURAN PROGRAM di main.py.
Contoh: ALGORITHM = "sa" dan DATASET = "small".
Parameter pencarian menggunakan nilai bawaan fungsi masing-masing algoritma.
Atur SHOW_PLOT = True jika ingin membuka jendela grafik.


- hill_climbing/hc_<waktu>/ berisi tiga percobaan HC.
- simulated_annealing/sa_<waktu>/ berisi tiga percobaan SA.
- genetic_algorithm/ga_<waktu>/ berisi 18 percobaan GA.
- Setiap sesi menyimpan dataset.json, session.json, dan summary.csv.
- Setiap run menyimpan run.json, history.csv, dan objective.png.
- SA juga menyimpan probabilities.csv dan probability.png pada setiap run.
- PNG dibuat oleh Matplotlib tanpa membuka dashboard atau jendela grafik.
- main.py tidak memerlukan Streamlit atau Plotly; cukup pasang Matplotlib.
- Dashboard membaca hasil tersimpan melalui src/result_io.py.
- Hasil dipisah ke hill_climbing/, simulated_annealing/, dan genetic_algorithm/.

run.json menyimpan state awal/akhir, termasuk kendaraan di luar, objective,
parameter, seed, iterasi, durasi, dan statistik khusus algoritma. GA juga menyimpan
populasi awal, populasi akhir, serta individu terbaik sepanjang pencarian.
history.csv berisi objective HC atau maksimum/rata-rata populasi GA per iterasi.
State dibaca bersama kapal dan kendaraan dari dataset.json pada sesi yang sama.

Plot setiap run berada di folder seed masing-masing:
- HC: objective.png (objective terhadap iterasi).
- SA: objective.png dan probability.png (probabilitas penerimaan terhadap iterasi).
- GA: objective.png (maksimum objective dan rata-rata populasi terhadap generasi).

Grafik gabungan tetap dibuat pada folder sesi, sejajar dengan summary.csv:
- HC: objective.png menampilkan tiga percobaan.
- SA: objective.png dan probability.png masing-masing menampilkan tiga percobaan.
- GA: objective_<kelompok>_pop-<P>_iter-<G>.png per konfigurasi, dengan tiga
  kurva maksimum dan tiga kurva rata-rata pada dua panel.

Dengan ALGORITHM = "all", main.py menjalankan tiga HC, tiga SA, dan delapan belas GA.
Dataset mengikuti nilai DATASET di main.py.

## Cakupan durasi

Run baru melalui main.py menyimpan duration_scope = "initialization_and_search"
di run.json. Durasi mencakup pembuatan state/populasi awal serta pencarian
untuk HC, SA, dan GA. Validasi hasil, penulisan berkas, dan plot berada di luar timer.
summary.csv juga memuat kolom Cakupan durasi.

Arsip lama tetap dipertahankan. HC lama hanya mencatat waktu pencarian
(search_only); SA/GA lama sudah mencakup inisialisasi. Jalankan ulang HC
untuk memperoleh durasi dengan cakupan yang sama. Pembaca ringkasan memberi
label cakupan tersebut pada arsip lama tanpa mengubah berkas aslinya.

list_sessions() mencari ketiga folder algoritma, termasuk simulated_annealing/.
