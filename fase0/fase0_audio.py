"""
SayIt - Fase 0: uji Speech-to-Text (STT) dan Text-to-Speech (TTS) di laptop Windows.

Perintah:
    python fase0_audio.py cek                              # cek lingkungan, mikrofon, dan suara TTS
    python fase0_audio.py rekam --penutur althof            # rekam kalimat uji (kondisi tenang)
    python fase0_audio.py rekam --penutur althof --kondisi bising
    python fase0_audio.py stt --model tiny base small       # uji faster-whisper
    python fase0_audio.py stt --model small --tanpa-prompt  # pembanding tanpa initial_prompt
    python fase0_audio.py tts                               # uji semua mesin TTS yang tersedia

Semua hasil disimpan di folder fase0_hasil/ di sebelah skrip ini.
"""
import argparse
import csv
import platform
import re
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "fase0_hasil"
REC_DIR = ROOT / "rekaman"
TTS_DIR = ROOT / "tts"
REC_LIST = REC_DIR / "daftar.csv"
SR = 16000

# id, teks, intent yang diharapkan (dipakai lagi nanti untuk uji intent router)
KALIMAT_UJI = [
    ("u1", "berapa nominal uang ini", "UANG"),
    ("u2", "tolong hitung uang kembalian saya", "UANG"),
    ("u3", "ini uang berapa rupiah", "UANG"),
    ("b1", "tolong bacakan tulisan di kertas ini", "BACA"),
    ("b2", "apa isi surat ini", "BACA"),
    ("b3", "baca dokumennya", "BACA"),
    ("k1", "kapan tanggal kedaluwarsanya", "KEDALUWARSA"),
    ("k2", "produk ini sudah expired belum", "KEDALUWARSA"),
    ("k3", "susu ini masih bisa diminum sampai kapan", "KEDALUWARSA"),
    ("k4", "tolong baca tanggal kedaluwarsa di kemasan ini", "KEDALUWARSA"),
    ("c1", "ulangi", "ULANGI"),
    ("c2", "lanjut", "LANJUT"),
    ("c3", "foto lagi", "FOTO_BARU"),
    ("c4", "kamu bisa bantu apa saja", "BANTUAN"),
    ("x1", "ini benda apa", "TIDAK_DIKENALI"),
]

WHISPER_PROMPT = ("uang, rupiah, nominal, kembalian, baca, bacakan, tulisan, dokumen, surat, "
                  "kedaluwarsa, expired, tanggal, ulangi, lanjut, foto lagi")

KALIMAT_TTS = [
    ("t1", "Foto berhasil diambil. Apa yang ingin kamu tanyakan?"),
    ("t2", "Terdeteksi tiga lembar: dua lembar lima puluh ribu rupiah dan satu lembar sepuluh ribu rupiah. "
           "Totalnya seratus sepuluh ribu rupiah."),
    ("t3", "Tanggal kedaluwarsa tiga Desember dua ribu dua puluh enam. Produk masih berlaku, sisa tujuh puluh delapan hari."),
    ("t4", "Maaf, saya tidak yakin. Coba foto ulang dengan uang terbuka penuh."),
]


# ----------------------------------------------------------------------------- util

def ada_internet(timeout=2.0):
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout).close()
        return True
    except OSError:
        return False


def normalisasi(teks):
    teks = teks.lower()
    teks = re.sub(r"[^\w\s]", " ", teks)
    return re.sub(r"\s+", " ", teks).strip()


def word_error_rate(ref, hyp):
    r, h = normalisasi(ref).split(), normalisasi(hyp).split()
    if not r:
        return 0.0 if not h else 1.0
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return d[len(h)] / len(r)


def p90(values):
    s = sorted(values)
    return s[min(len(s) - 1, int(round(0.9 * (len(s) - 1))))]


def cari_suara_indonesia(voices):
    hasil = []
    for v in voices:
        info = " ".join([str(v.id), str(v.name), " ".join(map(str, getattr(v, "languages", []) or []))]).lower()
        if any(k in info for k in ("indonesia", "id-id", "id_id", "andika", "gadis", "ardi")):
            hasil.append(v)
    return hasil


# ----------------------------------------------------------------------------- cek

def cmd_cek(_args):
    print(f"Python   : {sys.version.split()[0]}  ({platform.system()} {platform.release()})")
    if sys.version_info[:2] not in ((3, 10), (3, 11)):
        print("  Catatan: PRD menetapkan Python 3.10 atau 3.11. Versi lain mungkin tetap jalan.")
    print(f"Internet : {'tersedia' if ada_internet() else 'TIDAK tersedia'} "
          "(dibutuhkan hanya untuk mengunduh model pertama kali dan untuk gTTS)")

    print("\nPustaka:")
    for mod in ("faster_whisper", "sounddevice", "soundfile", "numpy", "pyttsx3", "transformers", "torch", "gtts"):
        try:
            m = __import__(mod)
            print(f"  [ok]    {mod} {getattr(m, '__version__', '')}")
        except Exception as e:
            print(f"  [belum] {mod}  ({type(e).__name__})")

    print("\nMikrofon:")
    try:
        import numpy as np
        import sounddevice as sd
        dev = sd.query_devices(kind="input")
        print(f"  Perangkat input default: {dev['name']}")
        print("  Merekam 2 detik untuk cek level suara... bicaralah sekarang.")
        audio = sd.rec(int(2 * SR), samplerate=SR, channels=1, dtype="float32")
        sd.wait()
        rms = float(np.sqrt(np.mean(audio ** 2)))
        status = "terlalu pelan, cek mikrofon" if rms < 0.005 else "ok"
        print(f"  Level RMS: {rms:.4f} -> {status}")
    except Exception as e:
        print(f"  Gagal mengakses mikrofon: {e}")

    print("\nSuara TTS Windows (SAPI5 via pyttsx3):")
    try:
        import pyttsx3
        eng = pyttsx3.init()
        voices = eng.getProperty("voices")
        for v in voices:
            print(f"  - {v.name}  |  {v.id}")
        indo = cari_suara_indonesia(voices)
        if indo:
            print(f"  Suara Indonesia ditemukan: {', '.join(v.name for v in indo)}")
        else:
            print("  Tidak ada suara Indonesia yang terlihat oleh pyttsx3.")
            print("  Coba: Settings > Time & language > Speech > Add voices > Bahasa Indonesia, lalu cek ulang.")
            print("  Jika sudah terpasang tetapi tetap tidak muncul, suara itu kemungkinan hanya tersedia")
            print("  untuk aplikasi Windows modern (OneCore) dan tidak terbaca oleh SAPI5.")
    except Exception as e:
        print(f"  pyttsx3 gagal: {e}")


# ----------------------------------------------------------------------------- rekam

def cmd_rekam(args):
    import sounddevice as sd
    import soundfile as sf

    REC_DIR.mkdir(parents=True, exist_ok=True)
    baru = not REC_LIST.exists()
    penutur = re.sub(r"\W+", "_", args.penutur.strip().lower())
    print(f"Penutur: {penutur} | kondisi: {args.kondisi} | durasi per kalimat: {args.durasi} detik")
    print("Bacakan kalimat dengan gaya bicara biasa, seperti sedang bertanya ke aplikasi.\n")

    with open(REC_LIST, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if baru:
            w.writerow(["file", "penutur", "kondisi", "id", "teks", "intent"])
        for kid, teks, intent in KALIMAT_UJI:
            nama = f"{penutur}_{args.kondisi}_{kid}.wav"
            while True:
                input(f'[{kid}] "{teks}"  -> tekan Enter lalu langsung bicara')
                audio = sd.rec(int(args.durasi * SR), samplerate=SR, channels=1, dtype="float32")
                sd.wait()
                sf.write(REC_DIR / nama, audio, SR, subtype="PCM_16")
                ulang = input("   Tersimpan. Enter = lanjut, r = rekam ulang: ").strip().lower()
                if ulang != "r":
                    break
            w.writerow([nama, penutur, args.kondisi, kid, teks, intent])
    print(f"\nSelesai. Daftar rekaman: {REC_LIST}")


# ----------------------------------------------------------------------------- stt

def baca_daftar_rekaman():
    if not REC_LIST.exists():
        sys.exit("Belum ada rekaman. Jalankan: python fase0_audio.py rekam --penutur <nama>")
    with open(REC_LIST, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # entri terakhir menang jika file yang sama direkam ulang
    unik = {r["file"]: r for r in rows}
    return [r for r in unik.values() if (REC_DIR / r["file"]).exists()]


def cmd_stt(args):
    import soundfile as sf
    from faster_whisper import WhisperModel

    rows = baca_daftar_rekaman()
    print(f"{len(rows)} rekaman ditemukan.")
    prompt = None if args.tanpa_prompt else WHISPER_PROMPT
    label_prompt = "tanpa_prompt" if args.tanpa_prompt else "dengan_prompt"
    out_csv = ROOT / "stt_hasil.csv"
    baru = not out_csv.exists()
    ringkasan = []

    with open(out_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if baru:
            w.writerow(["model", "prompt", "file", "penutur", "kondisi", "referensi", "transkrip",
                        "wer", "durasi_audio_s", "waktu_proses_s"])
        for size in args.model:
            print(f"\n=== Model {size} ({label_prompt}) ===")
            t0 = time.perf_counter()
            model = WhisperModel(size, device="cpu", compute_type="int8")
            waktu_muat = time.perf_counter() - t0
            print(f"Waktu muat model: {waktu_muat:.1f} s")

            # pemanasan agar waktu rekaman pertama tidak ikut menanggung inisialisasi
            _ = list(model.transcribe(str(REC_DIR / rows[0]["file"]), language="id")[0])

            wers, lat, rtf = [], [], []
            per_kondisi = {}
            for r in rows:
                path = REC_DIR / r["file"]
                dur = sf.info(str(path)).duration
                t = time.perf_counter()
                segments, _info = model.transcribe(str(path), language="id", beam_size=5,
                                                   vad_filter=True, initial_prompt=prompt)
                hyp = " ".join(s.text for s in segments).strip()   # generator: waktu dihitung setelah habis
                dt = time.perf_counter() - t
                wer = word_error_rate(r["teks"], hyp)
                wers.append(wer); lat.append(dt); rtf.append(dt / max(dur, 1e-6))
                per_kondisi.setdefault(r["kondisi"], []).append(wer)
                w.writerow([size, label_prompt, r["file"], r["penutur"], r["kondisi"], r["teks"], hyp,
                            f"{wer:.3f}", f"{dur:.2f}", f"{dt:.2f}"])
                tanda = "" if wer == 0 else "  <-- beda"
                print(f"  {r['file']:32s} WER {wer:4.0%} | {dt:4.1f}s | {hyp}{tanda}")

            ringkasan.append({
                "model": size, "prompt": label_prompt, "muat_s": waktu_muat,
                "wer_rata2": statistics.mean(wers), "latensi_median_s": statistics.median(lat),
                "latensi_p90_s": p90(lat), "rtf_median": statistics.median(rtf),
                "wer_per_kondisi": {k: statistics.mean(v) for k, v in per_kondisi.items()},
            })

    print("\n================ RINGKASAN STT ================")
    print(f"{'model':8s} {'prompt':14s} {'muat':>6s} {'WER':>6s} {'med':>6s} {'p90':>6s} {'RTF':>6s}  WER per kondisi")
    for s in ringkasan:
        kond = ", ".join(f"{k} {v:.0%}" for k, v in s["wer_per_kondisi"].items())
        print(f"{s['model']:8s} {s['prompt']:14s} {s['muat_s']:5.1f}s {s['wer_rata2']:6.1%} "
              f"{s['latensi_median_s']:5.1f}s {s['latensi_p90_s']:5.1f}s {s['rtf_median']:6.2f}  {kond}")
    print("\nPatokan PRD: WER <= 25%. Agar anggaran latensi total <= 8 detik tercapai,")
    print("latensi STT median sebaiknya <= 3 detik. Pilih model TERKECIL yang memenuhi keduanya.")
    print(f"Detail per rekaman: {out_csv}")


# ----------------------------------------------------------------------------- tts

def _pyttsx3_worker(args):
    """Dijalankan sebagai proses terpisah agar pyttsx3 tidak macet saat berganti suara."""
    import pyttsx3
    eng = pyttsx3.init()
    if args.voice_id:
        eng.setProperty("voice", args.voice_id)
    eng.setProperty("rate", args.rate)
    t = time.perf_counter()
    for kid, teks in KALIMAT_TTS:
        eng.save_to_file(teks, str(Path(args.out_dir) / f"{args.prefix}_{kid}.wav"))
    eng.runAndWait()
    print(f"ELAPSED={time.perf_counter() - t:.3f}")


def cmd_tts(args):
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    hasil = []

    # 1) pyttsx3 / SAPI5 (offline)
    try:
        import pyttsx3
        eng = pyttsx3.init()
        voices = eng.getProperty("voices")
        indo = cari_suara_indonesia(voices)
        kandidat = ([(v, True) for v in indo] or [(voices[0], False)]) if voices else []
        del eng
        for v, is_indo in kandidat:
            prefix = "sapi5_" + re.sub(r"\W+", "_", v.name.lower())[:30]
            label = v.name + ("" if is_indo else "  (BUKAN suara Indonesia, hanya pembanding)")
            print(f"[pyttsx3] {label}")
            p = subprocess.run([sys.executable, __file__, "_pyttsx3", "--voice-id", v.id, "--rate", str(args.rate),
                                "--out-dir", str(TTS_DIR), "--prefix", prefix],
                               capture_output=True, text=True, timeout=180)
            m = re.search(r"ELAPSED=([\d.]+)", p.stdout)
            if p.returncode == 0 and m:
                per = float(m.group(1)) / len(KALIMAT_TTS)
                hasil.append(("pyttsx3/SAPI5", label, "offline", 0.0, per))
            else:
                print(f"  gagal: {p.stderr.strip()[:300]}")
    except Exception as e:
        print(f"[pyttsx3] dilewati: {e}")

    # 2) MMS-TTS Indonesia (offline setelah unduhan pertama)
    try:
        import numpy as np
        import soundfile as sf
        import torch
        from transformers import AutoTokenizer, VitsModel, set_seed
        print("[MMS-TTS] memuat facebook/mms-tts-ind (unduhan pertama bisa lama)...")
        t = time.perf_counter()
        model = VitsModel.from_pretrained("facebook/mms-tts-ind")
        tok = AutoTokenizer.from_pretrained("facebook/mms-tts-ind")
        muat = time.perf_counter() - t
        waktu = []
        for kid, teks in KALIMAT_TTS:
            set_seed(555)   # model tidak deterministik
            t = time.perf_counter()
            inputs = tok(teks.lower(), return_tensors="pt")
            with torch.no_grad():
                wav = model(**inputs).waveform[0].cpu().numpy().astype(np.float32)
            waktu.append(time.perf_counter() - t)
            sf.write(TTS_DIR / f"mms_ind_{kid}.wav", wav, model.config.sampling_rate)
        hasil.append(("MMS-TTS", "facebook/mms-tts-ind (lisensi CC-BY-NC 4.0)", "offline", muat, statistics.mean(waktu)))
    except Exception as e:
        print(f"[MMS-TTS] dilewati: {type(e).__name__}: {e}")

    # 3) gTTS (ONLINE, hanya cadangan)
    if ada_internet():
        try:
            from gtts import gTTS
            waktu = []
            for kid, teks in KALIMAT_TTS:
                t = time.perf_counter()
                gTTS(teks, lang="id").save(str(TTS_DIR / f"gtts_{kid}.mp3"))
                waktu.append(time.perf_counter() - t)
            hasil.append(("gTTS", "Google (id)", "ONLINE", 0.0, statistics.mean(waktu)))
        except Exception as e:
            print(f"[gTTS] dilewati: {e}")
    else:
        print("[gTTS] dilewati: tidak ada internet")

    out_csv = ROOT / "tts_hasil.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mesin", "suara", "mode", "waktu_muat_s", "waktu_sintesis_rata2_s"])
        for row in hasil:
            w.writerow([row[0], row[1], row[2], f"{row[3]:.2f}", f"{row[4]:.2f}"])

    nilai_csv = ROOT / "penilaian_tts.csv"
    kosong = not nilai_csv.exists() or len(nilai_csv.read_text(encoding="utf-8").strip().splitlines()) <= 1
    if kosong and hasil:
        with open(nilai_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["penilai", "mesin", "kejelasan_1_5", "kealamian_1_5", "angka_terdengar_benar_ya_tidak", "catatan"])
            for row in hasil:
                w.writerow(["", row[0] + " | " + row[1], "", "", "", ""])

    print("\n================ RINGKASAN TTS ================")
    for m, s, mode, muat, per in hasil:
        print(f"{m:14s} {mode:8s} muat {muat:5.1f}s | sintesis {per:4.2f}s/kalimat | {s}")
    print(f"\nFile suara ada di: {TTS_DIR}")
    print(f"Minta minimal 3 anggota tim mendengarkan dan mengisi: {nilai_csv}")
    print("Patokan: pilih mesin OFFLINE dengan rata-rata kejelasan >= 4 dan sintesis <= 2 detik per kalimat.")


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="SayIt Fase 0: uji STT dan TTS")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("cek")

    r = sub.add_parser("rekam")
    r.add_argument("--penutur", required=True)
    r.add_argument("--kondisi", default="tenang", choices=["tenang", "bising"])
    r.add_argument("--durasi", type=float, default=4.0)

    s = sub.add_parser("stt")
    s.add_argument("--model", nargs="+", default=["tiny", "base", "small"])
    s.add_argument("--tanpa-prompt", action="store_true")

    t = sub.add_parser("tts")
    t.add_argument("--rate", type=int, default=170)

    w = sub.add_parser("_pyttsx3")
    w.add_argument("--voice-id", default="")
    w.add_argument("--rate", type=int, default=170)
    w.add_argument("--out-dir", required=True)
    w.add_argument("--prefix", required=True)

    args = ap.parse_args()
    {"cek": cmd_cek, "rekam": cmd_rekam, "stt": cmd_stt, "tts": cmd_tts, "_pyttsx3": _pyttsx3_worker}[args.cmd](args)


if __name__ == "__main__":
    main()
