"""Parser tanggal kedaluwarsa (PRD 8.8.1).

Masukannya teks hasil OCR, keluarannya tanggal yang dipilih beserta tingkat
keyakinannya. Tidak butuh model, data, atau internet, sehingga seluruh aturannya
bisa diuji tuntas.

Alur:
1. Pindai teks untuk kandidat tanggal. Posisi angka boleh berisi huruf yang
   sering tertukar saat OCR (O, I, L, S, B); huruf itu dikoreksi hanya di dalam
   kandidat, dan hanya pada bagian angkanya, agar nama bulan tidak ikut rusak
   ("SEP" tidak boleh menjadi "5EP").
2. Buang kandidat yang bukan tanggal kalender yang sah atau di luar rentang wajar.
3. Pilih satu tanggal: yang berdekatan dengan penanda (EXP, ED, BB, KEDALUWARSA,
   dan seterusnya) menang. Tanpa penanda, tanggal terjauh dipilih dan hasilnya
   ditandai kurang yakin. Bila dua tanggal sama-sama berpenanda, keduanya dibacakan.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field, replace
from datetime import date

from sayit.response.templates import (Utterance, ambiguous_expiry_response, expiry_response,
                                      fixed, unreadable_date_response)

# Huruf yang sering tertukar dengan angka pada hasil OCR (PRD 8.8.1).
# Sengaja hanya empat pasang yang disebut PRD. Menambah D atau G memperbesar
# peluang nama bulan ikut terbaca sebagai angka (DES, AGU), tanpa bukti untung.
OCR_DIGITS = {"O": "0", "I": "1", "L": "1", "S": "5", "B": "8"}
DIGITISH = "0-9" + "".join(OCR_DIGITS)

# Nama bulan Indonesia dan Inggris. Bentuk panjang didahulukan agar "MARET"
# tidak tercocok sebagai "MAR" lalu menyisakan "ET".
MONTH_NAMES: dict[int, list[str]] = {
    1: ["JANUARI", "JANUARY", "JAN"],
    2: ["FEBRUARI", "FEBRUARY", "FEB", "PEB"],
    3: ["MARET", "MARCH", "MAR"],
    4: ["APRIL", "APR"],
    5: ["MEI", "MAY"],
    6: ["JUNI", "JUNE", "JUN"],
    7: ["JULI", "JULY", "JUL"],
    8: ["AGUSTUS", "AUGUST", "AGU", "AGT", "AGS", "AUG"],
    9: ["SEPTEMBER", "SEPT", "SEP"],
    10: ["OKTOBER", "OCTOBER", "OKT", "OCT"],
    11: ["NOVEMBER", "NOPEMBER", "NOV", "NOP"],
    12: ["DESEMBER", "DECEMBER", "DES", "DEC"],
}
MONTH_BY_NAME = {nama: nomor for nomor, daftar in MONTH_NAMES.items() for nama in daftar}
_MONTH_ALT = "|".join(sorted(MONTH_BY_NAME, key=len, reverse=True))

# Tanggal yang seluruhnya angka TIDAK boleh dipisah spasi. Bila spasi diizinkan,
# "01/01/2026 12/12/2027" terbaca sebagai satu tanggal "2026 12/12" yang melintasi
# dua tanggal berbeda, dan tanggal kedua ikut hilang.
SEP = r"[./\-]"                         # pemisah tanggal hari-bulan-tahun serba angka
# Pasangan bulan-tahun dipecah dua pola. Dengan pemisah tercetak (12/2027) tidak ada
# ambiguitas. Dengan SPASI (12 2027) dua angka apa pun yang berdampingan bisa terbaca
# sebagai bulan dan tahun, jadi versi berspasi diberi penjaga penanda tersendiri.
SEP_TEXT = r"[./\-]"                     # pemisah bulan-tahun yang tercetak
# Spasi TIDAK dimasukkan ke SEP, tetapi dipakai pola `dmy_spasi` tersendiri yang
# mewajibkan KETIGA kelompok angka ada. Itulah yang membuatnya aman: pada
# "01/01/2026 12/12/2027" tidak ada tiga kelompok angka yang hanya dipisah spasi,
# sehingga tanggal kedua tetap utuh. Maksimum dua spasi, dan baris baru tidak
# diterima, supaya kecocokan tidak melompati batas baris OCR.
SEP_SPASI = r"[ ]{1,2}"
_D = f"[{DIGITISH}]"

# Urutan pola penting: yang paling banyak informasinya dicoba lebih dulu.
PATTERNS: list[tuple[str, re.Pattern]] = [
    # 2026.12.03 - tahun di depan, dikenali dari 4 digit pertama
    ("ymd", re.compile(rf"(?<![{DIGITISH}])({_D}{{4}}){SEP}({_D}{{1,2}}){SEP}({_D}{{1,2}})(?![{DIGITISH}])")),
    # 03/12/2026 dan 03-12-26
    ("dmy", re.compile(rf"(?<![{DIGITISH}])({_D}{{1,2}}){SEP}({_D}{{1,2}}){SEP}({_D}{{2,4}})(?![{DIGITISH}])")),
    # 08 10 26 - OCR kemasan sering mencetak pemisahnya sebagai spasi. Ditambahkan
    # 01-10 setelah terukur: pada `20261008` PaddleOCR membaca "EXP :08 10 26" dengan
    # benar, tetapi parser menolaknya. Dicoba sebelum pola bulan-tahun supaya
    # "08 10 26" tidak terpotong menjadi "08 10" lebih dulu.
    # Hari dan bulan wajib DUA digit. Tanggal cetak pada kemasan praktis selalu
    # berangka nol di depan, sedangkan satu digit membuat bacaan OCR yang terpotong
    # ikut diterima: ovaltine terbaca `EXP : 2 09 27` (seharusnya 27) dan dijawab
    # 2027-09-02. Pola serba-angka lain tetap menerima satu digit karena pemisahnya
    # eksplisit, jadi tidak ada ambiguitas serupa di sana.
    ("dmy_spasi", re.compile(rf"(?<![{DIGITISH}])({_D}{{2}}){SEP_SPASI}({_D}{{2}}){SEP_SPASI}"
                             rf"({_D}{{2,4}})(?![{DIGITISH}])")),
    # 03 DES 2026
    ("dmony", re.compile(rf"(?<![{DIGITISH}])({_D}{{1,2}})\s*{SEP}?\s*({_MONTH_ALT})\s*{SEP}?\s*({_D}{{2,4}})"
                         rf"(?![{DIGITISH}])")),
    # DES 2026 - tanpa hari
    ("mony", re.compile(rf"\b({_MONTH_ALT})\s*{SEP}?\s*({_D}{{2,4}})(?![{DIGITISH}])")),
    # 12/2027, 12/27, dan 12 2027 - tanpa hari
    ("my", re.compile(rf"(?<![{DIGITISH}])({_D}{{1,2}}){SEP_TEXT}({_D}{{2,4}})(?![{DIGITISH}])")),
    # 12 2027 - bulan-tahun berspasi, tahun WAJIB empat digit. Dipisah dari `my`
    # pada 02-10 setelah `'LOT 12 34 2028'` terbukti dijawab 2034-12-31 ("12 34" dibaca
    # Desember 2034). Pembedanya diambil dari PRD 8.8.1 sendiri, yang mendaftarkan
    # `MM/YY` (pemisah tercetak, tahun dua digit) dan `MM YYYY` (spasi, tahun empat
    # digit) - spasi dengan tahun dua digit tidak pernah diminta. Jadi syarat empat
    # digit menutup lubangnya TANPA menyimpang dari PRD dan tanpa penjaga penanda,
    # yang akan melanggar kewajiban format `MM YYYY`.
    ("my_spasi", re.compile(rf"(?<![{DIGITISH}])({_D}{{1,2}}){SEP_SPASI}({_D}{{4}})(?![{DIGITISH}])")),
    # 21082029 dan 210829 - tanpa pemisah sama sekali, lazim pada cetakan kemasan.
    # Dicoba paling akhir, dan hanya diterima bila ada penanda di dekatnya
    # (lihat find_candidates): enam angka berurutan juga bisa nomor bets.
    ("rapat8", re.compile(rf"(?<![{DIGITISH}])({_D}{{8}})(?![{DIGITISH}])")),
    ("rapat6", re.compile(rf"(?<![{DIGITISH}])({_D}{{6}})(?![{DIGITISH}])")),
]


@dataclass(frozen=True)
class DateCandidate:
    value: date                 # untuk tanggal tanpa hari, diisi hari terakhir bulan itu
    month_only: bool
    text: str                   # potongan teks asalnya, apa adanya
    start: int
    end: int
    pattern: str
    marker: str = ""            # penanda terdekat yang mendahuluinya
    corrected: bool = False     # ada huruf OCR yang dikoreksi menjadi angka
    swapped: bool = False       # urutan hari-bulan dibalik karena day-first tidak masuk akal


@dataclass
class DateParseResult:
    value: date | None = None
    month_only: bool = False
    confident: bool = False
    reason: str = ""
    candidates: list[DateCandidate] = field(default_factory=list)   # yang lolos validasi
    ambiguous: tuple[DateCandidate, DateCandidate] | None = None
    text: str = ""              # teks masukan, untuk dibacakan saat parser gagal

    @property
    def found(self) -> bool:
        return self.value is not None


# --------------------------------------------------------------------------- koreksi OCR

def fix_ocr_digits(potongan: str) -> str:
    """Ubah huruf yang tertukar menjadi angka. Hanya dipakai pada bagian angka.

    Huruf kecil ikut ditangani, karena "l" kecil justru yang paling sering
    tertukar dengan angka 1.
    """
    return "".join(OCR_DIGITS.get(c.upper(), c) for c in potongan)


def _as_number(potongan: str) -> int | None:
    """None bila potongan tidak memuat satu pun angka sungguhan.

    Penjaga ini mencegah kata biasa ikut terbaca: tanpa itu "SI" menjadi 51
    dan "BOLA" menjadi 8014.
    """
    if not any(c.isdigit() for c in potongan):
        return None
    return int(fix_ocr_digits(potongan))


# --------------------------------------------------------------------------- pembentukan tanggal

def expand_year(tahun: int, cfg: dict) -> int:
    dp = cfg["vision"]["date_parser"]
    return tahun if tahun >= 100 else int(dp["two_digit_year_base"]) + tahun


def end_of_month(tahun: int, bulan: int) -> date:
    return date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])


def make_date(tahun: int, bulan: int, hari: int | None) -> date | None:
    """None bila bukan tanggal kalender yang sah (termasuk 31 Februari)."""
    if not 1 <= bulan <= 12 or not 1 <= tahun <= 9999:
        return None
    if hari is None:
        return end_of_month(tahun, bulan)
    try:
        return date(tahun, bulan, hari)
    except ValueError:
        return None


def in_range(nilai: date, today: date, cfg: dict) -> bool:
    """Rentang wajar: beberapa tahun ke belakang sampai beberapa tahun ke depan."""
    dp = cfg["vision"]["date_parser"]
    try:
        awal = today.replace(year=today.year - int(dp["years_back"]))
        akhir = today.replace(year=today.year + int(dp["years_forward"]))
    except ValueError:                                   # today = 29 Februari
        awal = today.replace(year=today.year - int(dp["years_back"]), day=28)
        akhir = today.replace(year=today.year + int(dp["years_forward"]), day=28)
    return awal <= nilai <= akhir


# --------------------------------------------------------------------------- pemindaian

def _grup_angka(cocok: re.Match, jenis: str) -> list[str]:
    """Grup yang seharusnya berisi angka. Nama bulan tidak termasuk."""
    if jenis == "dmony":
        return [cocok.group(1), cocok.group(3)]
    if jenis == "mony":
        return [cocok.group(2)]
    return list(cocok.groups())


def _bukan_angka(cocok: re.Match, jenis: str) -> bool:
    """True bila ada grup angka yang sama sekali tidak memuat angka sungguhan."""
    return any(not any(c.isdigit() for c in g) for g in _grup_angka(cocok, jenis))


def _build(cocok: re.Match, jenis: str, cfg: dict) -> DateCandidate | None:
    asli = cocok.group(0)
    swapped = False

    angka = _grup_angka(cocok, jenis)
    if jenis == "ymd":
        tahun, bulan, hari = (_as_number(g) for g in angka)
        month_only = False
    elif jenis in ("dmy", "dmy_spasi"):
        hari, bulan, tahun = (_as_number(g) for g in angka)
        month_only = False
    elif jenis == "dmony":
        hari = _as_number(cocok.group(1))
        bulan = MONTH_BY_NAME[cocok.group(2)]
        tahun = _as_number(cocok.group(3))
        month_only = False
    elif jenis == "mony":
        hari = None
        bulan = MONTH_BY_NAME[cocok.group(1)]
        tahun = _as_number(cocok.group(2))
        month_only = True
    elif jenis in ("rapat6", "rapat8"):
        return _build_rapat(cocok, jenis, cfg)
    else:                                                # "my"
        hari = None
        bulan, tahun = (_as_number(g) for g in angka)
        month_only = True

    # hanya bagian angka yang diperiksa; nama bulan memang berisi huruf
    corrected = any(c in OCR_DIGITS for g in angka for c in g)

    if tahun is None or bulan is None or (hari is None and not month_only):
        return None
    tahun = expand_year(tahun, cfg)

    nilai = make_date(tahun, bulan, hari)
    if nilai is None and jenis in ("dmy", "dmy_spasi") and cfg["vision"]["date_parser"]["day_first"]:
        # 05/25/2027 tidak masuk akal sebagai hari-bulan; coba urutan bulan-hari
        nilai = make_date(tahun, hari, bulan)
        swapped = nilai is not None
    if nilai is None:
        return None

    return DateCandidate(value=nilai, month_only=month_only, text=asli,
                         start=cocok.start(), end=cocok.end(), pattern=jenis,
                         corrected=corrected, swapped=swapped)


def _build_rapat(cocok: re.Match, jenis: str, cfg: dict) -> DateCandidate | None:
    """Tanggal tanpa pemisah, misalnya 210829 atau 21082029.

    Urutan dicoba sesuai kebiasaan Indonesia lebih dulu (hari-bulan-tahun), lalu
    urutan terbalik. Yang tidak sah secara kalender langsung gugur, dan rentang
    tahun yang wajar menyaring sisanya.
    """
    utuh = cocok.group(1)
    if not any(c.isdigit() for c in utuh):
        return None
    d = fix_ocr_digits(utuh)
    if not d.isdigit():
        return None

    if jenis == "rapat6":                                # DDMMYY lalu YYMMDD
        urutan = [(d[0:2], d[2:4], d[4:6]), (d[4:6], d[2:4], d[0:2])]
    else:                                                # DDMMYYYY lalu YYYYMMDD
        urutan = [(d[0:2], d[2:4], d[4:8]), (d[6:8], d[4:6], d[0:4])]

    for hari_s, bulan_s, tahun_s in urutan:
        nilai = make_date(expand_year(int(tahun_s), cfg), int(bulan_s), int(hari_s))
        if nilai is not None:
            return DateCandidate(value=nilai, month_only=False, text=cocok.group(0),
                                 start=cocok.start(), end=cocok.end(), pattern=jenis,
                                 corrected=any(c in OCR_DIGITS for c in utuh))
    return None


def _nearest_marker(teks: str, mulai: int, cfg: dict, batas: int = 0) -> str:
    """Penanda terdekat yang mendahului kandidat, dalam jendela yang ditentukan.

    `batas` adalah akhir kandidat sebelumnya. Penanda yang berada di depan tanggal
    lain sudah menjadi milik tanggal itu: pada "EXP 01/06/2027 PROD 01/07/2027",
    kata EXP tidak boleh ikut diklaim oleh tanggal kedua.
    """
    dp = cfg["vision"]["date_parser"]
    jendela = int(dp["marker_window"])
    awal = max(batas, mulai - jendela)
    sebelum = teks[awal:mulai]
    ketemu = ""
    posisi = -1
    for m in dp["markers"]:
        pola = re.compile(rf"\b{re.escape(m.upper())}\b")
        for c in pola.finditer(sebelum):
            if c.start() > posisi:                       # penanda paling dekat yang menang
                posisi, ketemu = c.start(), m
    return ketemu


def _pola_berpenjaga(cfg: dict) -> tuple[str, ...]:
    """Awalan nama pola yang hanya dipercaya bila ada penanda di dekatnya.

    Dihitung dari config karena kedua saklarnya memang bisa berbeda: risiko pola
    rapat (bersaing dengan nomor bets) tidak sama dengan risiko pola berspasi
    (bersaing dengan deretan angka komposisi dan berat).
    """
    d = cfg["vision"]["date_parser"]
    awalan = []
    if d.get("require_marker_for_compact", True):
        awalan.append("rapat")
    if d.get("require_marker_for_spaced", True):
        awalan.append("dmy_spasi")
    # `my_spasi` TIDAK ikut dijaga penanda: PRD 8.8.1 mewajibkan format `MM YYYY`
    # didukung, dan mewajibkan penanda akan menolak "12 2027" yang sah.
    return tuple(awalan)


def find_candidates(teks: str, today: date, cfg: dict) -> list[DateCandidate]:
    """Semua tanggal sah yang ditemukan di teks, tanpa saling tumpang tindih."""
    besar = teks.upper()
    kandidat: list[DateCandidate] = []
    terpakai: list[tuple[int, int]] = []
    berpenjaga = _pola_berpenjaga(cfg)

    for jenis, pola in PATTERNS:
        pos = 0
        while (cocok := pola.search(besar, pos)) is not None:
            pos = cocok.end()
            if any(cocok.start() < b and a < cocok.end() for a, b in terpakai):
                continue                                 # sudah tercakup pola yang lebih lengkap
            dibuat = _build(cocok, jenis, cfg)
            if dibuat is None or not in_range(dibuat.value, today, cfg):
                # Kecocokan yang isinya bukan angka sungguhan tidak boleh menggeser
                # pemindaian sampai ujungnya. Pada "BB 12/2027", pola bulan-tahun
                # lebih dulu mencocokkan "B 12" (huruf B ada di tabel koreksi OCR);
                # kalau pemindaian lanjut dari ujung kecocokan itu, "12/2027" ikut
                # terlewat dan tanggalnya hilang sama sekali.
                # Sebaliknya tanggal yang memang tidak sah (32/12/2026) harus
                # dilompati utuh, kalau tidak potongannya ("2/12/2026") ikut terbaca.
                if _bukan_angka(cocok, jenis):
                    pos = cocok.start() + 1
                continue
            # Rentang diklaim SEKALIPUN kandidat ini nanti dibuang penjaga penanda.
            # Itu disengaja, dan diuji: 02-10 perilaku ini sempat dianggap bug dan
            # "diperbaiki" dengan melepas rentangnya bila penandanya tidak ada sama
            # sekali. Hasilnya justru dua jawaban SALAH baru, karena pola yang lebih
            # lemah lalu mendapat kesempatan menafsirkan angka yang sama:
            #   "NETTO 12 29 2028 G" -> 2029-12-31  (dari pola bulan-tahun "12 29")
            #   "LOT 11 27 2028 XY"  -> 2027-11-30
            # Dengan rentang tetap diklaim, keduanya DIAM. Jadi klaim rentang di sini
            # berfungsi sebagai penjaga: begitu sebuah rentang dinilai mencurigakan
            # oleh pola berpenjaga, tafsiran yang lebih lemah atas rentang yang sama
            # ikut ditekan. JANGAN dilepas tanpa mengukur benar/salah/diam lagi.
            terpakai.append((cocok.start(), cocok.end()))
            kandidat.append(dibuat)

    # Penanda dicocokkan setelah semua kandidat diketahui, agar satu penanda
    # tidak diklaim oleh dua tanggal sekaligus.
    hasil: list[DateCandidate] = []
    batas = 0
    for k in sorted(kandidat, key=lambda k: k.start):
        hasil.append(replace(k, marker=_nearest_marker(besar, k.start, cfg, batas=batas)))
        batas = k.end

    # Tanggal rapat tanpa pemisah hanya dipercaya bila ada penanda di dekatnya.
    # Tanpa syarat ini, nomor bets, kode produksi, dan barcode ikut terbaca
    # sebagai tanggal kedaluwarsa. Bisa dilonggarkan lewat config: pada potongan
    # zona yang sempit, potongan itu sendiri sudah menjadi bukti bahwa ini area
    # tanggal, sehingga penanda tidak lagi satu-satunya penjaga.
    if not berpenjaga:
        return hasil
    return [k for k in hasil if not k.pattern.startswith(berpenjaga) or k.marker]


# --------------------------------------------------------------------------- pemilihan

def pick(kandidat: list[DateCandidate], teks: str = "") -> DateParseResult:
    """Aturan pemilihan PRD 8.8.1."""
    if not kandidat:
        return DateParseResult(reason="tidak ada tanggal yang sah", text=teks)

    bertanda = [k for k in kandidat if k.marker]
    if bertanda:
        tanggal_unik = {k.value for k in bertanda}
        if len(tanggal_unik) > 1:
            dua = sorted(bertanda, key=lambda k: k.value)
            pasangan = (dua[0], dua[-1])
            return DateParseResult(value=dua[-1].value, month_only=dua[-1].month_only,
                                   confident=False, candidates=kandidat, ambiguous=pasangan,
                                   reason="dua tanggal sama-sama berpenanda", text=teks)
        pilihan = max(bertanda, key=lambda k: k.value)
        return DateParseResult(value=pilihan.value, month_only=pilihan.month_only, confident=True,
                               candidates=kandidat, reason=f"berdekatan dengan penanda {pilihan.marker!r}",
                               text=teks)

    if len(kandidat) == 1:
        satu = kandidat[0]
        return DateParseResult(value=satu.value, month_only=satu.month_only, confident=True,
                               candidates=kandidat, reason="hanya satu tanggal ditemukan", text=teks)

    # Tanpa penanda, tanggal terjauh yang dipilih: pada kemasan, tanggal produksi
    # selalu lebih awal daripada tanggal kedaluwarsa. Hasilnya kurang yakin.
    pilihan = max(kandidat, key=lambda k: k.value)
    return DateParseResult(value=pilihan.value, month_only=pilihan.month_only, confident=False,
                           candidates=kandidat, text=teks,
                           reason=f"{len(kandidat)} tanggal tanpa penanda, dipilih yang terjauh")


def parse_expiry(teks: str, today: date, cfg: dict) -> DateParseResult:
    """Cari dan pilih tanggal kedaluwarsa dari teks hasil OCR."""
    return pick(find_candidates(teks, today, cfg), teks=teks)


# --------------------------------------------------------------------------- ujaran

def expiry_utterance(hasil: DateParseResult, today: date) -> Utterance:
    """Ujaran untuk pengguna, sesuai tingkat keyakinan parser."""
    if not hasil.found:
        if hasil.text.strip():
            return unreadable_date_response(hasil.text.strip())
        return fixed("tidak_ada_tanggal")
    if hasil.ambiguous is not None:
        a, b = hasil.ambiguous
        return ambiguous_expiry_response(a.value, b.value, today,
                                         month_only=a.month_only and b.month_only)
    return expiry_response(hasil.value, today, month_only=hasil.month_only,
                           confident=hasil.confident)
