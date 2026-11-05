# Perubahan UI web — branch `feature/app/page`

Semua perubahan di bawah ini hanya menyentuh `web/app/page.js`, kecuali yang
disebut lain. Angka yang ditulis di sini **terukur di peramban**, bukan taksiran.

Dasar perbandingannya `main` pada `8093acd`.

---

## 1. Sembilan temuan UI/UX diperbaiki

### Interaksi

**Ketukan layar selagi sistem bicara kini hanya menyela, tidak ikut memotret.**
Sambutan diputar tepat saat layar kamera terbuka, jadi pengguna yang mengetuk
untuk memotongnya selalu memotret sebelum sempat membidik.

**Rana jadi tombol sungguhan** (`<button aria-label="Ambil foto">`), bukan `div`
tanpa nama yang tidak bisa disebut pembaca layar. Logika jepretnya dipisah ke
`ambilFoto()` supaya tombol rana dan ketukan layar tidak menyimpang.

**Nada 1320 Hz dan "Silakan bicara" sebelum mikrofon menyala**, di `LISTENING_Q`
dan `LISTENING_MENU`. Sebelumnya mikrofon menyala tanpa bunyi apa pun; satu-satunya
tandanya bola yang berubah warna, dan itu hanya terlihat. Nadanya sengaja berbeda
dari bip 880 Hz yang berarti "sudah kudengar".

**Penutupan otomatis diumumkan pada detik ke-20**, dan sistem yang sedang bicara
kini dihitung sebagai aktivitas. Ini sekaligus menutup utang lama: satu potongan
bacaan dokumen terukur 29,6 detik, hanya 0,4 detik dari batas 30 detik, sehingga
aplikasi bisa menutup di tengah jawabannya sendiri.

### Kontras dan ukuran

| | sebelum | sesudah |
| :--- | ---: | ---: |
| Teks putih di kartu jawaban | 2,86:1 | **5,18:1** |
| Ikon tombol | 2,96:1 | **4,31:1** |
| Teks jawaban | 15px | 18px |
| Teks pertanyaan | 19px | 20px |

Latar kartu dan warna ikon pindah dari `#f97316`/`#ea580c` ke `#c2410c`
(konstanta `JINGGA_TEKS`). Ambang WCAG AA adalah 4,5:1 untuk teks dan 3:1 untuk
ikon, jadi keduanya dulu gagal. `#f97316` tetap dipakai sebagai aksen yang tidak
memuat teks: bingkai bidik dan rana.

### Bahasa dan semantik

- `"anda"` → `"kamu"` di layar pertanyaan, menyamakannya dengan audio `/foto`.
- Tiga tombol ikon dapat **label terlihat** (Ulangi, Foto lagi, Keluar), ikonnya
  `aria-hidden`, dan `aria-label`-nya memuat label itu (WCAG 2.5.3 Label in Name).
- Satu `h1` "SayIt" tersembunyi, supaya pembaca layar punya judul untuk menavigasi.
- Alt foto, galat kamera, galat jaringan, dan teks layar selesai diganti supaya
  menyebut **tindakan berikutnya**, bukan hanya kesalahannya.

---

## 2. Mode demo `?demo=1`

Dipakai ketika backend tidak bisa dijalankan, supaya tampilan dan urutan layar
tetap bisa diuji. Buka `http://localhost:3000/?demo=1`.

Terukur: **delapan ucapan berurutan** dari sambutan sampai "Sampai jumpa",
**0 panggilan ke `/api`**, dan `window.close()` terpanggil sekali di ujungnya.

Empat titik dicegat saat `DEMO` menyala:

| Fungsi | Perilaku di mode demo |
| :--- | :--- |
| `kirim()` | jawaban palsu berbentuk sama dengan balasan server |
| `klipSrc()` | klip diambil dari `web/public/demo`, bukan `/api/klip` |
| `dengarkan()` | mikrofon tidak dibuka sama sekali |
| prefetch | teks klip dari salinan lokal `KLIP_DEMO` |

Alurnya juga jalan di perangkat **tanpa kamera**: kegagalan `getUserMedia` tetap
masuk ke `CAMERA_READY`, dan `/foto` tidak lagi memanggil `fetch(null)`.

### Suaranya sungguhan, jawabannya tidak

`web/public/demo/` berisi 10 berkas, 460 KB, dibuat `scripts/buat_demo_suara.py`:

- delapan klip **disalin apa adanya** dari `assets/tts`;
- `jawaban_uang.mp3` dirender dari `money_response` + `tindak_lanjut`, jadi ia
  memakai rangkaian klip kata yang **sama** dengan aplikasi penuh. Ini disengaja:
  kalau dirender sebagai satu kalimat utuh, demo akan terdengar lebih mulus
  daripada aslinya, dan itu menyesatkan;
- `jawaban_berkas.mp3` lewat jalur teks dinamis.

Teks di `JAWAB_DEMO` wajib sama persis dengan isi audionya. Skrip itu mencetak
teksnya supaya keduanya tidak pernah menyimpang.

Ada penanda merah **"MODE DEMO - jawaban palsu"** di layar, dan sejak 05-11 penanda
itu juga **BERBUNYI**: peringatannya diucapkan tepat sesudah sambutan selesai, dan
masuk wilayah `aria-live` sejak halaman dibuka. Penanda yang hanya terlihat
melanggar aturan nomor 1 di README - pengguna sasaran SayIt tidak melihat layar,
jadi ia akan mendengar "lima puluh empat ribu rupiah" tanpa tahu itu karangan.
Diucapkan SESUDAH sambutan, bukan sebelum, karena `putar()` memanggil
`speechSynthesis.cancel()` sehingga peringatan yang lebih dulu akan terpotong. Jawaban dan
latensinya karangan, jadi jangan dipakai menilai akurasi atau kecepatan. Mutu
suara justru boleh dinilai dari sini, karena mesinnya sama.

---

## 3. Menyela ucapan dan lebar kolom

**Bug: `hentikanSuara()` tidak pernah menjeda elemen `<audio>`.** Ia hanya
menaikkan `utteranceId`, yang membatalkan rantai alurnya tetapi membiarkan
klipnya berbunyi sampai habis. Dulu tidak kelihatan karena ketukan langsung
memicu klip berikutnya, dan `putar()` menjeda yang lama. Sejak ketukan saat
sistem bicara hanya menyela tanpa memulai apa pun, menyela jadi tidak membungkam
apa pun: sambutan 10 detik terus bicara walau layar diketuk.

Terukur sebelum: `play sambutan.mp3`, `pause` **0 kali**.
Terukur sesudah: `pause sambutan.mp3` pada **detik 2,1**.

**Kolom isi dibatasi 560 px.** Diukur pada layar laptop 1279x573:

| | sebelum | sesudah |
| :--- | ---: | ---: |
| Lebar kartu jawaban | 921px | 538px |
| Karakter per baris | **102** | **60** |
| Lebar tiap tombol | 299px | 172px |

Rentang nyaman membaca 45–75 karakter per baris. Foto ikut dibatasi supaya foto,
kartu, dan tombol membentuk satu kolom.

**Orb di layar pertanyaan tidak lagi terpotong.** `top: 86%` ditambah setengah
tinggi orb (117px) melewati tepi layar begitu tingginya di bawah 836px. Diuji
pada elemen probe:

| tinggi layar | sebelum | sesudah |
| ---: | ---: | ---: |
| 573px | terpotong 37px | aman, sisa 8px |
| 812px | terpotong 3px | aman, sisa 8px |
| 900px | sudah aman | tidak berubah |

---

## Yang diperiksa dan ternyata tidak bermasalah

- **Fokus keyboard.** Tab mendarat di tombol pertama, `:focus-visible` cocok,
  cincin fokus bawaan peramban tampil.
- **Galat hydration** yang sempat muncul di Chrome: HTML dari server identik
  dengan hasil render klien, dan di peramban bersih tanpa ekstensi galat itu
  tidak muncul sama sekali.
- Badge **"N"** di pojok kiri bawah adalah indikator dev Next.js, bukan bagian
  aplikasi, dan hilang di build produksi.

## Yang belum diuji

- Kamera, mikrofon, dan pembacaan TalkBack atau VoiceOver. Panel uji memblokir
  akses perangkat, jadi semua ini hanya bisa dicoba sendiri oleh pengguna.
- Bunyi sebenarnya di telinga. Yang bisa dibuktikan hanya berkas yang benar
  terambil dan diputar, bukan bagaimana kedengarannya.
- Perbaikan orb dibuktikan lewat elemen probe, bukan di aplikasi berjalan.
- Mode demo masih ada di kode produksi. Tinggal dihapus kalau tidak diperlukan,
  dan `web/public/demo` (460 KB) ikut ter-deploy walau hanya aktif dengan `?demo=1`.

## Catatan untuk yang melanjutkan

Jangan jalankan `npm run build` selagi `npm run dev` hidup. Keduanya memakai
folder `.next` yang sama, dan build produksi akan menimpa artefak yang sedang
dipakai dev server sehingga halamannya membalas HTTP 500
(`__webpack_modules__[moduleId] is not a function`). Obatnya hentikan dev server,
hapus `web/.next`, lalu jalankan lagi.
