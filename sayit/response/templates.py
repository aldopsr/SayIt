"""Templat respons suara SayIt.

Setiap respons disusun sebagai *Utterance*: daftar bagian yang berupa
- Clip  : klip suara yang sudah disimpan (kalimat tetap, frasa, kata angka, nama bulan)
- Pause : jeda
- Text  : teks bebas yang harus disintesis saat itu juga (butuh internet untuk gTTS)

Respons uang dan tanggal hanya memakai Clip dan Pause, sehingga tetap bisa
diputar tanpa internet setelah klip dibuat dengan scripts/build_tts_cache.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Union

from sayit.response.terbilang import NUMBER_WORDS, terbilang_tokens


@dataclass(frozen=True)
class Clip:
    key: str


@dataclass(frozen=True)
class Pause:
    kind: str = "short"   # "short" (koma) atau "long" (titik)


@dataclass(frozen=True)
class Text:
    text: str


Part = Union[Clip, Pause, Text]
Utterance = list  # list[Part]

# --------------------------------------------------------------------------- kosakata klip

FIXED_PHRASES: dict[str, str] = {
    # SENGAJA PENDEK. Versi sebelumnya menyebut setiap perintah dan berdurasi 22
    # detik - pengguna yang sudah hafal harus menunggu tiap kali membuka aplikasi.
    # Daftar lengkapnya pindah ke menu_bantuan, yang dipanggil dengan "apa itu SayIt".
    # Barge-in tetap jadi jaring pengaman, tetapi menyela seharusnya tidak PERLU.
    "sambutan": ("Halo, ini SayIt. Sentuh layar di mana saja untuk memotret. "
                 "Kalau belum paham, katakan: apa itu SayIt."),
    "sentuh_untuk_berkas": ("Sentuh layar sekali untuk membuka daftar berkas."),
    "tindak_lanjut": "Mau saya ulangi, foto lagi, atau keluar?",
    "sampai_jumpa": "Sampai jumpa.",
    "foto_diambil": "Foto berhasil diambil. Apa yang ingin kamu tanyakan?",
    "belum_ada_foto": "Belum ada foto. Silakan ambil foto terlebih dahulu.",
    "silakan_foto": "Silakan ambil foto baru.",
    "sedang_memproses": "Sebentar, sedang saya proses.",
    "suara_tidak_jelas": "Maaf, suaramu tidak terdengar jelas. Coba ulangi.",
    "tidak_mengerti": ("Maaf, saya belum mengerti. Kamu bisa bertanya tentang nominal uang, "
                       "membacakan tulisan, atau tanggal kedaluwarsa."),
    "menu_bantuan": ("Saya bisa membantu tiga hal: menyebutkan nominal uang kertas, membacakan tulisan, "
                     "dan membacakan tanggal kedaluwarsa. Ambil foto, lalu ajukan pertanyaanmu. "
                     "Semua tombol juga bisa dipanggil dengan suara. Katakan putar kamera untuk "
                     "berganti kamera, pilih berkas untuk membaca berkas dari penyimpanan, ulangi "
                     "untuk mendengar jawaban sekali lagi, foto lagi untuk memotret ulang, atau "
                     "keluar untuk menutup aplikasi. "
                     "Saya tidak bisa memeriksa keaslian uang."),
    "foto_buram": "Foto terlihat buram. Coba pegang kamera lebih diam, lalu foto ulang.",
    "foto_gelap": "Foto terlalu gelap. Coba dekatkan ke lampu, lalu foto ulang.",
    "foto_terang": "Foto terlalu terang atau silau. Coba ubah sudut kamera, lalu foto ulang.",
    "foto_kecil": "Resolusi foto terlalu kecil. Coba foto ulang dari jarak lebih dekat.",
    "tidak_ada_uang": "Saya tidak menemukan uang kertas di foto. Pastikan uang berada di tengah dan tidak tertutup jari.",
    "tidak_yakin_uang": "Saya tidak yakin dengan nominal uang ini. Coba foto ulang dengan uang terbuka penuh.",
    "tidak_ada_tulisan": "Saya tidak menemukan tulisan yang bisa dibaca. Coba foto ulang lebih dekat dan lebih terang.",
    # Galat unggahan berkas: nama berkasnya sengaja tidak disebut supaya kalimatnya
    # tetap bisa jadi klip tersimpan. Pengguna sudah tahu berkas mana yang dipilihnya.
    "berkas_tidak_didukung": ("Jenis berkas itu tidak didukung. Pilih berkas gambar, PDF, "
                              "atau dokumen Word, lalu coba lagi."),
    "berkas_rusak": "Berkas itu tidak bisa dibaca atau rusak. Coba pilih berkas yang lain.",
    "berkas_lain": ("Kamu bisa memilih berkas lain yang lebih jelas, "
                    "atau memotret langsung dengan menyentuh layar."),
    # Kendali tombol lewat suara. Pengguna tunanetra tidak melihat tombolnya,
    # jadi hasil tiap tindakan harus diucapkan, bukan hanya terjadi.
    "kamera_diputar": "Baik, kameranya saya putar.",
    "kamera_depan": "Kamera depan aktif.",
    "kamera_belakang": "Kamera belakang aktif.",
    "kamera_tunggal": ("Perangkat ini hanya punya satu kamera. "
                       "Kamu masih bisa memilih berkas dari penyimpanan."),
    "buka_berkas": "Silakan pilih berkas dari penyimpanan.",
    "tidak_ada_tanggal": "Saya tidak menemukan tanggal kedaluwarsa. Coba foto bagian kemasan yang lain.",
    "tulisan_bukan_tanggal": ("Saya menemukan tulisan, tetapi tidak yakin itu tanggal kedaluwarsa. "
                              "Tulisannya:"),
    "dua_tanggal": "Saya menemukan dua tanggal. Yang pertama:",
    "p_yang_kedua": "Yang kedua:",
    "butuh_internet": "Maaf, membacakan tulisan ini membutuhkan koneksi internet.",
    "modul_belum_siap": ("Maaf, fitur ini belum bisa dipakai di perangkat ini. "
                         "Kamu masih bisa mencoba fitur yang lain."),
    "tidak_ada_ulangan": "Belum ada jawaban yang bisa diulang.",
    "tidak_ada_lanjutan": "Tidak ada bagian berikutnya. Semua tulisan sudah dibacakan.",
    "katakan_lanjut": "Katakan lanjut untuk mendengar bagian berikutnya.",
    "hari_terakhir": "Hari ini adalah hari terakhir produk berlaku.",
    # frasa penyusun
    "p_uang": "Uang",
    "p_rupiah": "rupiah",
    "p_terdeteksi": "Terdeteksi",
    "p_lembar": "lembar",
    "p_dan": "dan",
    "p_totalnya": "Totalnya",
    "p_tanggal_kedaluwarsa": "Tanggal kedaluwarsa",
    "p_berlaku_sampai": "Berlaku sampai",
    "p_masih_berlaku_sisa": "Produk masih berlaku, sisa",
    "p_hari": "hari",
    # Satuan waktu yang lebih besar. "tiga ratus dua puluh tujuh hari" tidak bisa
    # dibayangkan siapa pun; "sekitar sebelas bulan" langsung terbayang.
    "p_minggu": "minggu",
    "p_bulan": "bulan",
    "p_tahun": "tahun",
    "p_sekitar": "sekitar",
    "p_minggu_lalu": "minggu lalu",
    "p_bulan_lalu": "bulan lalu",
    "p_tahun_lalu": "tahun lalu",
    "p_sudah_lewat_sejak": "Produk sudah melewati tanggal kedaluwarsa sejak",
    "p_hari_lalu": "hari lalu",
    "p_kurang_yakin_tanggal": "Saya kurang yakin, tetapi tanggal yang terbaca adalah",
}

MONTHS = ["januari", "februari", "maret", "april", "mei", "juni",
          "juli", "agustus", "september", "oktober", "november", "desember"]

CLIP_TEXTS: dict[str, str] = {
    **FIXED_PHRASES,
    **{f"n_{w}": w for w in NUMBER_WORDS},
    **{f"m_{m}": m.capitalize() for m in MONTHS},
}

VALID_NOMINALS = (1000, 2000, 5000, 10000, 20000, 50000, 100000)


def number_clips(n: int) -> list[Part]:
    return [Clip(f"n_{w}") for w in terbilang_tokens(n)]


# Ambang satuan waktu. Di bawah seminggu tetap dihitung hari, karena di situlah
# ketelitian benar-benar berguna: "sisa tiga hari" menentukan tindakan hari ini.
# Di atas itu angka harian justru menyembunyikan maknanya.
BATAS_MINGGU = 7
BATAS_BULAN = 60          # ~2 bulan; di bawah ini "delapan minggu" masih terbayang
BATAS_TAHUN = 365


def durasi_clips(hari: int, lampau: bool = False) -> list[Part]:
    """Ubah jumlah hari menjadi satuan yang bisa dibayangkan.

    `lampau=True` memakai bentuk "... lalu". Pembulatan disertai kata "sekitar",
    supaya sistem tidak terdengar lebih yakin daripada yang sebenarnya - angka
    bulat hasil pembagian BUKAN tanggal pasti, dan pengguna tunanetra tidak punya
    cara lain memeriksanya.
    """
    hari = abs(int(hari))
    if hari < BATAS_MINGGU:
        return [*number_clips(hari), Clip("p_hari_lalu" if lampau else "p_hari")]

    if hari < BATAS_BULAN:
        n, satuan = round(hari / 7), "minggu"
    elif hari < BATAS_TAHUN:
        n, satuan = round(hari / 30), "bulan"
    else:
        n, satuan = round(hari / 365), "tahun"
    n = max(1, n)                       # pembulatan ke bawah tidak boleh jadi nol

    kunci = f"p_{satuan}_lalu" if lampau else f"p_{satuan}"
    return [Clip("p_sekitar"), *number_clips(n), Clip(kunci)]


def date_clips(d: date, month_only: bool = False) -> list[Part]:
    parts: list[Part] = [] if month_only else number_clips(d.day)
    parts.append(Clip(f"m_{MONTHS[d.month - 1]}"))
    parts += number_clips(d.year)
    return parts


def fixed(key: str) -> Utterance:
    if key not in FIXED_PHRASES:
        raise KeyError(f"Kalimat tetap tidak dikenal: {key}")
    return [Clip(key)]


# --------------------------------------------------------------------------- uang

def money_response(counts: dict[int, int]) -> Utterance:
    """counts: {nominal: jumlah lembar}. Contoh {50000: 2, 10000: 1}."""
    counts = {int(k): int(v) for k, v in counts.items() if int(v) > 0}
    bad = set(counts) - set(VALID_NOMINALS)
    if bad:
        raise ValueError(f"Nominal tidak valid: {sorted(bad)}")
    sheets = sum(counts.values())
    if sheets == 0:
        return fixed("tidak_ada_uang")

    total = sum(k * v for k, v in counts.items())
    if sheets == 1:
        (nominal,) = counts
        return [Clip("p_uang"), *number_clips(nominal), Clip("p_rupiah"), Pause("long")]

    utt: Utterance = [Clip("p_terdeteksi"), *number_clips(sheets), Clip("p_lembar"), Pause("short")]
    items = sorted(counts.items(), key=lambda kv: -kv[0])
    for i, (nominal, n) in enumerate(items):
        if i > 0:
            utt += [Pause("short")]
            if i == len(items) - 1:
                utt.append(Clip("p_dan"))
        utt += [*number_clips(n), Clip("p_lembar"), *number_clips(nominal), Clip("p_rupiah")]
    utt += [Pause("long"), Clip("p_totalnya"), *number_clips(total), Clip("p_rupiah"), Pause("long")]
    return utt


# --------------------------------------------------------------------------- tanggal kedaluwarsa

def expiry_response(expiry: date, today: date, month_only: bool = False, confident: bool = True) -> Utterance:
    """expiry: untuk tanggal tanpa hari (month_only=True), isi dengan hari terakhir bulan tersebut."""
    utt: Utterance = []
    if not confident:
        utt += [Clip("p_kurang_yakin_tanggal")]
    elif month_only:
        utt += [Clip("p_berlaku_sampai")]
    else:
        utt += [Clip("p_tanggal_kedaluwarsa")]
    utt += date_clips(expiry, month_only=month_only)
    utt.append(Pause("long"))

    delta = (expiry - today).days
    if delta > 0:
        utt += [Clip("p_masih_berlaku_sisa"), *durasi_clips(delta), Pause("long")]
    elif delta == 0:
        utt += [Clip("hari_terakhir")]
    else:
        utt += [Clip("p_sudah_lewat_sejak"), *durasi_clips(-delta, lampau=True), Pause("long")]
    return utt


def ambiguous_expiry_response(pertama: date, kedua: date, today: date,
                              month_only: bool = False) -> Utterance:
    """Dua tanggal sama-sama mungkin (PRD 8.8.1): keduanya dibacakan, tanpa mengklaim yakin."""
    utt: Utterance = [Clip("dua_tanggal"), *date_clips(pertama, month_only=month_only), Pause("long"),
                      Clip("p_yang_kedua"), *date_clips(kedua, month_only=month_only), Pause("long")]
    return utt + expiry_response(max(pertama, kedua), today, month_only=month_only, confident=False)


def unreadable_date_response(tulisan: str) -> Utterance:
    """Ada tulisan tetapi bukan tanggal yang sah (PRD 8.9). Tulisannya dibacakan apa adanya."""
    return [Clip("tulisan_bukan_tanggal"), Pause("short"), Text(tulisan), Pause("long")]


# --------------------------------------------------------------------------- teks bebas (dokumen)

_SENT_RE = re.compile(r"(?<=[.!?])\s+")


def split_chunks(text: str, max_words: int = 40) -> list[str]:
    """Potong teks panjang menjadi bagian per kalimat, masing-masing sekitar max_words kata."""
    sentences = [s.strip() for s in _SENT_RE.split(re.sub(r"\s+", " ", text).strip()) if s.strip()]
    chunks, cur = [], []
    for s in sentences:
        words = s.split()
        if cur and len(cur) + len(words) > max_words:
            chunks.append(" ".join(cur))
            cur = []
        cur += words
        while len(cur) > max_words:            # kalimat yang sangat panjang dipotong paksa
            chunks.append(" ".join(cur[:max_words]))
            cur = cur[max_words:]
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def document_chunk_response(chunk: str, has_more: bool) -> Utterance:
    utt: Utterance = [Text(chunk)]
    if has_more:
        utt += [Pause("long"), Clip("katakan_lanjut")]
    return utt


# --------------------------------------------------------------------------- utilitas

def clip_keys(utt: Utterance) -> set[str]:
    return {p.key for p in utt if isinstance(p, Clip)}


def to_plain_text(utt: Utterance) -> str:
    """Versi teks dari ujaran, untuk log dan tampilan layar."""
    out = ""
    for p in utt:
        if isinstance(p, Clip):
            out += " " + CLIP_TEXTS[p.key]
        elif isinstance(p, Text):
            out += " " + p.text
        elif isinstance(p, Pause):
            out = out.rstrip()
            if not out.endswith((".", ",", "?", "!", ":")):
                out += "." if p.kind == "long" else ","
    out = re.sub(r"\s+", " ", out).strip()
    return re.sub(r"([.?!])\s+(\w)", lambda m: f"{m.group(1)} {m.group(2).upper()}", out)
