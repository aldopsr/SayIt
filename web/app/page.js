"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";

/* Alur (lihat docs/deploy.md):
   mulai  -> sentuh layar: sambutan diputar
   foto   -> sentuh layar DI MANA SAJA: ambil foto, mutunya diperiksa
   tanya  -> tahan tombol: rekam pertanyaan, lepas: kirim
   jawab  -> audio memuat jawaban + "mau saya ulangi, foto lagi, atau keluar?"
             lalu kembali ke tanya untuk mendengar jawabannya          */

/** webm/opus dari MediaRecorder tidak terbaca soundfile di server.
 *  Browser sudah punya decodernya, jadi didecode di sini lalu dikemas jadi WAV 16-bit. */
async function keWav(blob) {
  // Tekan sekejap -> potongan belum keluar -> blob kosong -> decodeAudioData
  // melempar EncodingError. Dijaga supaya pengguna dapat pesan, bukan layar galat.
  if (blob.size < 1024) throw new Error("terlalu-pendek");

  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  let buf;
  try {
    buf = await ctx.decodeAudioData(await blob.arrayBuffer());
  } catch {
    ctx.close();
    throw new Error("terlalu-pendek");
  }
  if (buf.duration < 0.3) {
    ctx.close();
    throw new Error("terlalu-pendek");
  }
  const pcm = buf.getChannelData(0);
  const out = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const tulis = (o, s) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)));

  tulis(0, "RIFF");
  out.setUint32(4, 36 + pcm.length * 2, true);
  tulis(8, "WAVEfmt ");
  out.setUint32(16, 16, true);
  out.setUint16(20, 1, true);
  out.setUint16(22, 1, true);
  out.setUint32(24, buf.sampleRate, true);
  out.setUint32(28, buf.sampleRate * 2, true);
  out.setUint16(32, 2, true);
  out.setUint16(34, 16, true);
  tulis(36, "data");
  out.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) {
    const v = Math.max(-1, Math.min(1, pcm[i]));
    out.setInt16(44 + i * 2, v * 0x7fff, true);
  }
  ctx.close();
  return new Blob([out], { type: "audio/wav" });
}

export default function Page() {
  const video = useRef(null);
  const rekamanRef = useRef(null);
  const potonganRef = useRef([]);
  const audioRef = useRef(null);
  const tungguRef = useRef(null);

  const [fase, setFase] = useState("mulai");   // mulai | foto | proses | tanya | merekam
  const [pesan, setPesan] = useState("");
  const [galat, setGalat] = useState("");

  /** Satu elemen audio dipakai ulang: klip baru memotong yang lama, jadi
   *  pengguna tidak pernah mendengar dua suara bertumpuk. */
  const bunyikan = useCallback((src) => {
    window.speechSynthesis?.cancel();
    audioRef.current?.pause();
    const a = new Audio(src);
    audioRef.current = a;
    a.play().catch(() => {});
  }, []);

  /** Peringatan harus DIDENGAR, bukan hanya tampil, dan tiap kalimatnya menyebut
   *  jalan keluarnya - penggunanya tunanetra dan tidak melihat layar.
   *
   *  Dipakai speechSynthesis bawaan peramban, bukan klip dari server, karena
   *  sebagian peringatan ini justru muncul KETIKA servernya tidak terjangkau.
   *  Galat yang datang dari server tetap memakai klip gTTS lewat bunyikan(). */
  const peringatkan = useCallback((teks) => {
    setGalat(teks);
    audioRef.current?.pause();
    const s = window.speechSynthesis;
    if (!s) return;                       // pembaca layar masih dapat lewat aria-live
    s.cancel();
    const u = new SpeechSynthesisUtterance(teks);
    u.lang = "id-ID";
    s.speak(u);
  }, []);

  useEffect(() => {
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => { if (video.current) video.current.srcObject = s; })
      // Belum ada gestur pengguna di sini, dan iOS memblokir speechSynthesis
      // sebelum gestur. Jadi hanya dicatat; sentuhan pertama yang membunyikannya.
      .catch(() => setGalat(
        "Kamera belum diizinkan. Buka pengaturan izin situs di peramban, nyalakan kamera, " +
        "lalu muat ulang halaman. Sementara itu kamu masih bisa memilih berkas dari penyimpanan."
      ));
  }, []);

  // Langkah 4 dan 7: kalau prosesnya lama, beri tahu dengan suara.
  const mulaiTunggu = () => {
    clearTimeout(tungguRef.current);
    tungguRef.current = setTimeout(() => bunyikan("/api/klip/sedang_memproses.mp3"), 2000);
  };
  const selesaiTunggu = () => clearTimeout(tungguRef.current);

  function fotoSekarang() {
    const v = video.current;
    if (!v?.videoWidth) return Promise.resolve(null);
    const c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext("2d").drawImage(v, 0, 0);
    return new Promise((r) => c.toBlob(r, "image/jpeg", 0.92));
  }

  async function kirim(url, form) {
    setFase("proses");
    setGalat("");
    mulaiTunggu();
    try {
      const r = await fetch(url, { method: "POST", body: form });
      if (!r.ok) throw new Error(`status-${r.status}`);
      const j = await r.json();
      selesaiTunggu();
      if (j.error) {
        // Pesan dari server sudah dalam bahasa pengguna dan sudah membawa audionya,
        // jadi jangan ditimpa - cukup bunyikan.
        setGalat(j.error);
        if (j.audio) bunyikan(`data:audio/wav;base64,${j.audio}`);
        else peringatkan(j.error);
        setFase(url.endsWith("/tanya") ? "tanya" : "foto");
        return;
      }
      setPesan(j.teks);
      bunyikan(`data:audio/wav;base64,${j.audio}`);

      // Mutu ditolak -> tetap di langkah foto, alasannya sudah dibacakan. Diperiksa
      // lewat `diterima`, bukan lewat URL: /berkas juga bisa ditolak quality gate,
      // dan menyuruh bertanya tentang foto yang tidak pernah diterima membuat
      // pengguna tunanetra bicara ke ruang kosong.
      if (j.diterima !== undefined) setFase(j.diterima ? "tanya" : "foto");
      else if (j.intent === "FOTO_BARU") setFase("foto");
      else if (j.intent === "KELUAR") setFase("mulai");
      else setFase("tanya");
    } catch (e) {
      selesaiTunggu();
      // Server yang MENJAWAB galat tidak sama dengan server yang tidak terjangkau.
      // Menyuruh pengguna tunanetra memeriksa internetnya padahal internetnya baik
      // membuatnya mengejar masalah yang salah.
      peringatkan(
        String(e.message).startsWith("status-")
          ? "Server menolak permintaan ini. Coba sekali lagi, atau pilih berkas yang lain."
          : "Tidak bisa menghubungi server. Periksa koneksi internetmu, lalu coba lagi."
      );
      setFase(url.endsWith("/foto") ? "foto" : "tanya");
    }
  }

  async function sentuhLayar() {
    if (fase === "mulai") {
      // Kamera gagal sebelum ada gestur, jadi peringatannya belum bisa berbunyi tadi.
      // Sambutannya pun akan menyesatkan karena menyuruh memotret. Peringatan dulu;
      // fase tetap pindah supaya tombol "pilih berkas" muncul sebagai jalan keluar.
      if (galat) { peringatkan(galat); setFase("foto"); return; }
      // Browser memblokir autoplay sampai ada gestur, jadi sambutan menunggu sentuhan pertama.
      bunyikan("/api/klip/sambutan.mp3");
      setPesan("Sentuh layar di mana saja untuk mengambil foto.");
      setFase("foto");
      return;
    }
    if (fase !== "foto") return;
    const foto = await fotoSekarang();
    if (!foto) {
      peringatkan("Kamera belum siap. Tunggu sebentar, lalu sentuh layar lagi. "
                  + "Kalau tetap gagal, pilih berkas dari penyimpanan.");
      return;
    }
    const form = new FormData();
    form.append("foto", foto, "foto.jpg");
    kirim("/api/foto", form);
  }

  function pilihBerkas(e) {
    const f = e.target.files?.[0];
    e.target.value = "";                 // berkas yang sama bisa dipilih lagi
    if (!f) return;
    const form = new FormData();
    form.append("berkas", f, f.name);
    kirim("/api/berkas", form);
  }

  async function mulaiRekam() {
    if (fase !== "tanya") return;
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      potonganRef.current = [];
      const mr = new MediaRecorder(s);
      mr.ondataavailable = (e) => e.data.size && potonganRef.current.push(e.data);
      mr.onstop = async () => {
        s.getTracks().forEach((t) => t.stop());
        try {
          const form = new FormData();
          const mentah = new Blob(potonganRef.current, { type: mr.mimeType });
          form.append("suara", await keWav(mentah), "tanya.wav");
          kirim("/api/tanya", form);
        } catch (e) {
          setFase("tanya");
          peringatkan(
            e.message === "terlalu-pendek"
              ? "Rekamannya terlalu pendek. Tahan tombolnya sampai selesai bicara, baru lepas."
              : "Suaramu tidak bisa dibaca. Tahan tombolnya lalu bicara lebih dekat ke mikrofon, "
                + "atau ketik pertanyaanmu di kotak teks."
          );
        }
      };
      mr.start(250);               // potongan tiap 250 ms, jadi tekanan singkat pun berisi
      rekamanRef.current = mr;
      setFase("merekam");
    } catch {
      peringatkan("Mikrofon belum diizinkan. Buka pengaturan izin situs di peramban, "
                  + "nyalakan mikrofon, lalu tahan tombolnya lagi. "
                  + "Kamu juga bisa mengetik pertanyaanmu di kotak teks di bawah tombol.");
    }
  }

  function selesaiRekam() {
    if (rekamanRef.current?.state === "recording") rekamanRef.current.stop();
  }

  function kirimTeks(e) {
    e.preventDefault();
    const teks = new FormData(e.target).get("teks")?.toString().trim();
    if (!teks || fase !== "tanya") return;
    const form = new FormData();
    form.append("teks", teks);
    e.target.reset();
    kirim("/api/tanya", form);
  }

  const judul = {
    mulai: "Sentuh layar untuk mulai",
    foto: "Sentuh layar untuk memotret",
    proses: "Sedang saya proses",
    tanya: "Tahan tombol lalu bertanya",
    merekam: "Lepas untuk mengirim",
  }[fase];

  const bolehSentuh = fase === "mulai" || fase === "foto";

  return (
    <main style={{ height: "100dvh", display: "flex", flexDirection: "column" }}>
      <video
        ref={video}
        autoPlay
        muted
        playsInline
        aria-hidden="true"
        style={{ position: "fixed", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: 0.45 }}
      />

      {/* Sentuh di MANA SAJA untuk memotret. Hanya hidup di fase foto, jadi tombol
          rekam dan kotak teks tidak pernah tertutup olehnya. */}
      {bolehSentuh && (
        <button
          onPointerDown={sentuhLayar}
          aria-label={judul}
          style={{
            position: "fixed", inset: 0, zIndex: 1,
            background: "transparent", border: "none", cursor: "pointer",
            WebkitTapHighlightColor: "transparent",
          }}
        />
      )}

      <div style={{ position: "relative", zIndex: 2, padding: "28px 24px 0", pointerEvents: "none" }}>
        <img src="/logo.png" alt="SayIt" width={88} height={87} />
      </div>

      <div style={{ position: "relative", zIndex: 2, flex: 1, display: "grid", placeItems: "center", padding: "0 24px", textAlign: "center", pointerEvents: "none" }}>
        <p style={{ fontSize: 22, lineHeight: 1.35, color: galat ? "#ff6b6b" : "var(--putih)" }}>
          {galat || pesan || judul}
        </p>
      </div>

      {/* Jawaban diumumkan pembaca layar walau layarnya tidak dilihat. */}
      <p className="sr" role="status" aria-live="assertive">{galat || pesan}</p>

      <div style={{ position: "relative", zIndex: 2, display: "grid", placeItems: "center", gap: 18, padding: "0 24px 42px", paddingBottom: "max(42px, env(safe-area-inset-bottom))" }}>
        {fase === "foto" && (
          <label
            style={{
              display: "inline-block", padding: "15px 26px", borderRadius: 14,
              background: "#11161a", color: "var(--jingga)", fontSize: 17, fontWeight: 600,
              cursor: "pointer", border: "1px solid #2a2f33",
            }}
          >
            Pilih berkas dari penyimpanan
            <input
              type="file"
              accept="image/*,.pdf,.docx"
              onChange={pilihBerkas}
              aria-label="Pilih gambar, PDF, atau DOCX dari penyimpanan"
              style={{ position: "absolute", width: 1, height: 1, opacity: 0 }}
            />
          </label>
        )}

        {!bolehSentuh && (
          <>
            <motion.button
              onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); mulaiRekam(); }}
              onPointerUp={selesaiRekam}
              onPointerCancel={selesaiRekam}
              disabled={fase === "proses"}
              aria-label={judul}
              animate={{ scale: fase === "merekam" ? 1.08 : 1 }}
              whileTap={{ scale: 0.97 }}
              transition={{ type: "spring", bounce: fase === "merekam" ? 0.35 : 0, duration: 0.4 }}
              style={{
                width: 184, height: 184, borderRadius: "50%", border: "none",
                background: fase === "proses" ? "var(--abu)" : "var(--jingga)",
                color: "#fff", fontSize: 19, fontWeight: 600, cursor: "pointer",
                touchAction: "none", WebkitTapHighlightColor: "transparent",
                boxShadow: fase === "merekam" ? "0 0 0 14px rgba(254,115,0,.22)" : "0 10px 34px rgba(254,115,0,.3)",
              }}
            >
              {judul}
            </motion.button>

            <form onSubmit={kirimTeks} style={{ display: "flex", gap: 8, width: "100%", maxWidth: 420 }}>
              <input
                name="teks"
                placeholder="atau ketik pertanyaan"
                aria-label="Ketik pertanyaan"
                style={{ flex: 1, padding: "13px 16px", borderRadius: 13, border: "1px solid #2a2f33", background: "#11161a", color: "var(--putih)", fontSize: 16 }}
              />
              <button
                type="submit"
                style={{ padding: "13px 20px", borderRadius: 13, border: "none", background: "#11161a", color: "var(--jingga)", fontSize: 16, fontWeight: 600, cursor: "pointer" }}
              >
                Kirim
              </button>
            </form>
          </>
        )}
      </div>
    </main>
  );
}
