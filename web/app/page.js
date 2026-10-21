'use client';

import { useState, useEffect, useRef } from 'react';

// === KOMPONEN AI ORB (BOLA PARTIKEL + GELOMBANG FREKUENSI DARI PARTIKEL YANG SAMA) ===
// Gelombang audio tidak digambar sebagai bidang terpisah, tapi terdiri dari titik-titik (partikel) dengan
// gaya yang sama seperti bolanya. Saat ada suara, titik-titik itu "keluar" dari bola dan membentuk
// puncak-puncak frekuensi, lalu masuk lagi ke bola saat suara mereda.
// mode:
//  - 'idle'      : tidak ada suara -> titik gelombang menyatu kembali ke bola, bola tenang bernapas pelan
//  - 'speaking'  : sistem sedang berbicara -> puncak lebar & lembut, bergerak pelan, oranye
//  - 'listening' : user sedang input suara -> puncak lebih rapat & cepat, oranye-merah pekat, bola mengerut
// levelRef (opsional): ref berisi angka 0..1 dari volume mic asli untuk mode 'listening'.
//   Kalau tidak diisi, amplitudo suara user disimulasikan.
const ORB_MODES = {
  idle:      { amp: 0.05, speed: 0.4, bars: 0, glow: 0.22, radius: 1.0,  pulse: 0.02, mix: 0, r: 251, g: 140, b: 50 },
  speaking:  { amp: 0.10, speed: 1.4, bars: 1, glow: 0.4,  radius: 1.03, pulse: 0.06, mix: 0, r: 249, g: 115, b: 22 },
  listening: { amp: 0.12, speed: 2.0, bars: 1, glow: 0.45, radius: 0.95, pulse: 0.05, mix: 1, r: 225, g: 70,  b: 12 },
};

// Lapisan gelombang. n1/n2 harus bilangan bulat supaya gelombang menyambung mulus mengelilingi bola.
const WAVE_LAYERS = [
  { n1: 3, n2: 7,  s1: 1.3,  s2: -0.9, ph: 0.0, a: 1.0 },
  { n1: 4, n2: 9,  s1: -1.1, s2: 1.4,  ph: 1.7, a: 0.8 },
  { n1: 2, n2: 6,  s1: 0.8,  s2: -1.2, ph: 3.1, a: 0.9 },
  { n1: 5, n2: 11, s1: 1.7,  s2: 1.0,  ph: 4.4, a: 0.7 },
];
const WAVE_COLORS_SPEAKING  = [[249,115,22], [251,146,60], [234,88,12], [245,158,11]];
const WAVE_COLORS_LISTENING = [[225,60,20],  [244,90,60],  [190,40,20], [239,68,68]];
const WAVE_SAMPLES = 160;
const WAVE_DOTS = 2400;

// Ambang RMS mikrofon: di bawah ini dianggap hening. Dikalibrasi kasar di laptop;
// ponytail: satu angka, bukan AGC - naikkan kalau ruangnya berisik.
const AMBANG_SUARA = 0.015;
const HENING_MS = 3000;    // spec 4: berhenti mendengar setelah 3 detik hening
const IDLE_MS = 30000;     // spec 7: tutup aplikasi setelah 30 detik tanpa interaksi

function AiParticleOrb({ width = 260, height = 260, mode = 'idle', levelRef = null }) {
  const canvasRef = useRef(null);
  const modeRef = useRef(mode);
  modeRef.current = mode;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Resolusi tajam di layar HP (retina)
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Sebaran titik di bola (fibonacci sphere)
    const N = 650;
    const golden = Math.PI * (3 - Math.sqrt(5));
    const particles = [];
    for (let i = 0; i < N; i++) {
      const y = 1 - (2 * (i + 0.5)) / N;
      const ring = Math.sqrt(1 - y * y);
      const theta = golden * i;
      particles.push({
        x0: Math.cos(theta) * ring,
        y0: y,
        z0: Math.sin(theta) * ring,
        phi: Math.acos(y),
        theta,
      });
    }

    const R = width * 0.235;
    const cx = width / 2;
    const cy = height / 2;
    const fov = 260;
    const TWO_PI = Math.PI * 2;

    const lerp = (a, b, t) => a + (b - a) * t;
    const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
    const frac = (v) => v - Math.floor(v);

    // Titik-titik gelombang: tiap titik punya sudut (theta), jarak tetap dari bola (u: 0..1),
    // dan lapisan. Sebaran 2D merata (low-discrepancy) supaya kerapatannya mirip titik di bola.
    const dots = [];
    for (let j = 0; j < WAVE_DOTS; j++) {
      dots.push({
        theta: frac((j + 1) * 0.7548776662) * TWO_PI,
        u: frac((j + 1) * 0.5698402910),
        layer: j % 4,
        front: Math.floor(j / 4) % 2 === 1, // sebagian di depan bola, sebagian di belakang
        ph: frac((j + 1) * 0.3247179572) * TWO_PI,
      });
    }
    const shapes = WAVE_LAYERS.map(() => new Float32Array(WAVE_SAMPLES));

    const cur = { ...ORB_MODES.idle }; // nilai yang dihaluskan antar mode
    let spin = 0, wave = 0, wt = 0, time = 0, env = 0;
    let last = performance.now();
    let raf;

    // Hitung profil tinggi gelombang (0..1) tiap lapisan di sekeliling bola
    const computeShapes = () => {
      for (let k = 0; k < WAVE_LAYERS.length; k++) {
        const L = WAVE_LAYERS[k];
        const arr = shapes[k];
        for (let n = 0; n < WAVE_SAMPLES; n++) {
          const th = (n / WAVE_SAMPLES) * TWO_PI - Math.PI / 2;
          // speaking: puncak lebar & lambat, listening: puncak rapat & cepat
          const sS = Math.pow(0.55 * (0.5 + 0.5 * Math.sin(th * L.n1 + wt * L.s1 + L.ph)) + 0.45 * (0.5 + 0.5 * Math.sin(th * L.n2 - wt * L.s2 + L.ph * 0.7)), 1.15);
          const sL = Math.pow(0.55 * (0.5 + 0.5 * Math.sin(th * L.n1 * 2 + wt * L.s1 * 1.6 + L.ph)) + 0.45 * (0.5 + 0.5 * Math.sin(th * L.n2 * 2 - wt * L.s2 * 1.6 + L.ph * 0.7)), 1.15);
          arr[n] = sS + (sL - sS) * cur.mix;
        }
      }
    };

    // Gambar titik-titik gelombang (pass belakang atau depan bola)
    const drawWaveDots = (front, baseR) => {
      if (cur.bars < 0.02) return;
      const innerR = baseR * 0.9; // mulai sedikit di dalam bola supaya menyatu
      const softEdge = R * 0.14;
      const amps = WAVE_LAYERS.map((L) => L.a * R * 1.0);
      const live = cur.bars * (0.25 + 0.75 * env);

      for (let i = 0; i < dots.length; i++) {
        const d = dots[i];
        if (d.front !== front) continue;

        const hMax = amps[d.layer];
        const rho = d.u * hMax;                                  // jarak titik dari bola kalau gelombang penuh
        const idx = Math.min(WAVE_SAMPLES - 1, (d.theta / TWO_PI * WAVE_SAMPLES) | 0);
        const H = shapes[d.layer][idx] * hMax * live;            // tinggi gelombang saat ini di sudut ini
        const vis = clamp((H - rho) / softEdge, 0, 1);           // titik muncul kalau gelombang sudah sampai ke posisinya
        if (vis <= 0) continue;

        const rr = innerR + rho * (1 + 0.05 * Math.sin(time * 2.5 + d.ph));
        const ang = d.theta - Math.PI / 2;
        const px = cx + Math.cos(ang) * rr;
        const py = cy + Math.sin(ang) * rr;

        const far = rho / hMax; // 0 dekat bola, 1 ujung gelombang
        const c0 = WAVE_COLORS_SPEAKING[d.layer], c1 = WAVE_COLORS_LISTENING[d.layer];
        const cr = lerp(lerp(c0[0], c1[0], cur.mix), 253, far * 0.45);
        const cg = lerp(lerp(c0[1], c1[1], cur.mix), 186, far * 0.45);
        const cb = lerp(lerp(c0[2], c1[2], cur.mix), 116, far * 0.45);
        const alpha = (0.4 + 0.6 * (1 - far * 0.6)) * vis * (front ? 1 : 0.7);
        const size = (1.3 + 0.9 * (1 - far)) * (0.9 + 0.25 * env) * (0.6 + 0.4 * vis);

        ctx.fillStyle = `rgba(${cr | 0},${cg | 0},${cb | 0},${alpha.toFixed(2)})`;
        ctx.beginPath();
        ctx.arc(px, py, size, 0, TWO_PI);
        ctx.fill();
      }

      // Kontur: deretan titik di tepi tiap gelombang, supaya bentuk frekuensinya jelas terbaca
      for (let k = 0; k < WAVE_LAYERS.length; k++) {
        if ((k % 2 === 1) !== front) continue;
        const hMax = amps[k];
        const c0 = WAVE_COLORS_SPEAKING[k], c1 = WAVE_COLORS_LISTENING[k];
        ctx.fillStyle = `rgba(${lerp(c0[0], c1[0], cur.mix) | 0},${lerp(c0[1], c1[1], cur.mix) | 0},${lerp(c0[2], c1[2], cur.mix) | 0},0.9)`;
        for (let n = 0; n < WAVE_SAMPLES; n += 2) {
          const H = shapes[k][n] * hMax * live;
          if (H < 3) continue;
          const ang = (n / WAVE_SAMPLES) * TWO_PI - Math.PI / 2;
          ctx.beginPath();
          ctx.arc(cx + Math.cos(ang) * (innerR + H), cy + Math.sin(ang) * (innerR + H), 1.5, 0, TWO_PI);
          ctx.fill();
        }
      }
    };

    const render = (now) => {
      const dt = clamp((now - last) / 1000, 0.001, 0.05);
      last = now;
      time += dt;

      const mode = modeRef.current;
      const target = ORB_MODES[mode] || ORB_MODES.idle;

      // Transisi halus antar mode
      const k = 1 - Math.exp(-dt * 5);
      for (const key in target) cur[key] += (target[key] - cur[key]) * k;

      spin += dt * cur.speed * 0.45;
      wave += dt * cur.speed * 3.2;
      wt += dt * (1 + 0.9 * cur.mix);

      // Envelope "suara" 0..1
      let rawEnv;
      if (mode === 'speaking') {
        const syl = Math.abs(Math.sin(time * 5.1) * 0.5 + Math.sin(time * 8.3 + 1) * 0.3 + Math.sin(time * 13.7) * 0.2);
        rawEnv = 0.2 + 0.8 * syl;
      } else if (mode === 'listening') {
        if (levelRef && typeof levelRef.current === 'number') {
          rawEnv = clamp(levelRef.current, 0, 1);
        } else {
          const voice = Math.abs(Math.sin(time * 3.7) * 0.6 + Math.sin(time * 9.1) * 0.4);
          rawEnv = 0.15 + 0.85 * voice * (0.6 + 0.4 * Math.sin(time * 0.9));
        }
      } else {
        rawEnv = 0.5 + 0.5 * Math.sin(time * 1.1);
      }
      env += (rawEnv - env) * (1 - Math.exp(-dt * 14));

      const colStr = (a) => `rgba(${cur.r | 0},${cur.g | 0},${cur.b | 0},${a.toFixed(3)})`;
      const baseR = R * cur.radius * (1 + cur.pulse * env * 2);

      ctx.clearRect(0, 0, width, height);

      // Glow lembut di belakang bola
      const grad = ctx.createRadialGradient(cx, cy, R * 0.2, cx, cy, width / 2);
      grad.addColorStop(0, colStr(cur.glow * (0.4 + 0.6 * env)));
      grad.addColorStop(1, colStr(0));
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, width, height);

      if (cur.bars >= 0.02) computeShapes();

      // Titik gelombang yang berada di belakang bola
      drawWaveDots(false, baseR);

      // Partikel bola
      const cosY = Math.cos(spin), sinY = Math.sin(spin);
      const tilt = 0.35 + Math.sin(time * 0.4) * 0.08;
      const cosX = Math.cos(tilt), sinX = Math.sin(tilt);

      const pts = particles.map((p) => {
        const wS = Math.sin(p.phi * 5 - wave) * (0.7 + 0.3 * Math.cos(p.theta * 2 + wave * 0.5));
        const wL = Math.sin(p.phi * 8 + wave * 0.7) * Math.cos(p.theta * 6 - wave * 0.5);
        const w = wS + (wL - wS) * cur.mix;
        const r = baseR + w * baseR * cur.amp * (0.3 + 0.7 * env);

        const x = p.x0 * r, y = p.y0 * r, z = p.z0 * r;
        const x1 = x * cosY - z * sinY;
        const z1 = x * sinY + z * cosY;
        const y2 = y * cosX - z1 * sinX;
        const z2 = y * sinX + z1 * cosX;

        const scale = fov / (fov + baseR - z2); // z besar = dekat kamera
        return { px: cx + x1 * scale, py: cy + y2 * scale, z: z2, scale };
      });

      pts.sort((a, b) => a.z - b.z);

      for (const p of pts) {
        const depth = clamp((p.z + baseR * 1.4) / (baseR * 2.8), 0, 1);
        const rr = lerp(253, cur.r, depth);
        const gg = lerp(186, cur.g, depth);
        const bb = lerp(116, cur.b, depth);
        const alpha = 0.35 + 0.65 * depth;
        const size = (1.0 + 1.9 * depth) * p.scale * (1 + 0.2 * env * cur.bars);

        ctx.fillStyle = `rgba(${rr | 0},${gg | 0},${bb | 0},${alpha.toFixed(2)})`;
        ctx.beginPath();
        ctx.arc(p.px, p.py, size, 0, Math.PI * 2);
        ctx.fill();
      }

      // Titik gelombang yang berada di depan bola
      drawWaveDots(true, baseR);

      raf = requestAnimationFrame(render);
    };

    raf = requestAnimationFrame(render);
    return () => cancelAnimationFrame(raf);
  }, [width, height, levelRef]);

  return <canvas ref={canvasRef} style={{ display: 'block', width, height }} />;
}

// === LOGO SAYIT (inline SVG dari sayit-light.svg, tanpa background, tampil di semua screen) ===
function SayItLogo({ height = 36 }) {
  return (
    <svg
      role="img"
      aria-label="SayIt"
      xmlns="http://www.w3.org/2000/svg"
      width={(height * 800) / 280}
      height={height}
      viewBox="0 0 800 280"
      style={{ display: 'block' }}
    >
      <g transform="translate(70 0)">
        <g transform="translate(66 40)">
          <g fill="none" stroke="#FF6900" strokeWidth="23" strokeLinecap="round" strokeLinejoin="round">
            <path d="M58 22H32Q12 22 12 42V62 M130 22H156Q176 22 176 42V62 M12 130V150Q12 170 32 170H58 M130 170H156Q176 170 176 150V130" />
            <path d="M58 86V114 M94 61V139 M130 86V114" />
          </g>
        </g>
        <text x="294" y="191" fill="#111111" fontFamily="Arial, Helvetica, sans-serif" fontSize="134" fontWeight="700" letterSpacing="-6">SayIt</text>
      </g>
    </svg>
  );
}

export default function SayItPage() {
  // === STATE MANAGEMENT ===
  const [appState, setAppState] = useState('INIT');
  const [srText, setSrText] = useState('');
  const [resultText, setResultText] = useState('');
  const [capturedImage, setCapturedImage] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false); // sistem sedang berbicara (TTS)
  const [facingMode, setFacingMode] = useState('user'); // 'user' = kamera depan, 'environment' = kamera belakang
  const [capturedMirror, setCapturedMirror] = useState(true); // foto dari kamera depan ditampilkan mirror, kamera belakang & upload tidak
  const [orbSlot, setOrbSlot] = useState({ top: null, scale: 0.9 }); // posisi orb di layar hasil

  // === REFS ===
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const facingRef = useRef('user');
  const isFlipping = useRef(false);
  const fileInputRef = useRef(null);
  const isSpeechSynthesisSpeaking = useRef(false);
  const utteranceId = useRef(0);
  const orbSlotRef = useRef(null);
  const nivRef = useRef(0);                        // volume mic 0..1, dibaca orb
  const aktifRef = useRef(0);                      // kapan terakhir ada aktivitas (sentuh ATAU suara)
  const timersRef = useRef([]);
  const hentiDengarRef = useRef(null);             // membatalkan sesi mendengar yang berjalan
  const dengarGen = useRef(0);                     // penjaga sesi mendengar, lihat dengarkan()

  // === KELOMPOK LAYAR ===
  // Dideklarasikan di atas karena efek timer idle (spec 7) membacanya, dan const
  // tidak boleh dibaca sebelum baris deklarasinya.
  const isCamera = appState === 'INIT' || appState === 'CAMERA_READY';
  const isProcessing = appState === 'PROCESSING_VISION' || appState === 'PROCESSING_Q';
  const isQuestionScreen = appState === 'PROMPTING_Q' || appState === 'LISTENING_Q';
  const isResultScreen = appState === 'SHOWING_RESULT' || appState === 'PROMPTING_MENU'
    || appState === 'LISTENING_MENU' || appState === 'HASIL_SUNYI';

  // === TIMER: semua perpindahan state tertunda lewat sini ===
  // Timer yang tertinggal adalah AKAR dari bug "Foto Lagi butuh dua klik": timer
  // lama (onend -> nextState, atau simulasi mendengar) menimpa state yang baru
  // saja diset oleh klik pengguna. Jadi tiap perpindahan state membatalkannya dulu.
  const bersihkanTimer = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  };
  const nanti = (fn, ms) => { timersRef.current.push(setTimeout(fn, ms)); };

  /** Satu-satunya jalan berpindah state. Membatalkan timer dan sesi mendengar dulu. */
  const pindah = (state) => {
    bersihkanTimer();
    dengarGen.current++;                           // batalkan sesi dengar yang belum mulai
    if (hentiDengarRef.current) hentiDengarRef.current();
    setAppState(state);
  };

  /** Hentikan ucapan sistem (barge-in).
   *
   *  utteranceId WAJIB ikut dinaikkan: cancel() memicu onend, dan tanpa ini onend
   *  itu masih dianggap sah lalu menjadwalkan perpindahan state yang tidak diminta
   *  pengguna - persis kebalikan dari maksud barge-in. */
  const hentikanSuara = () => {
    utteranceId.current++;
    if (typeof window !== 'undefined') window.speechSynthesis?.cancel();
    isSpeechSynthesisSpeaking.current = false;
    setIsSpeaking(false);
  };

  // === FUNGSI UTILITAS: AUDIO & AKSESIBILITAS ===
  const playSystemAudio = (textUtama, nextStateDelay = null, selesai = null) => {
    setSrText(textUtama);

    window.speechSynthesis.cancel();
    const id = ++utteranceId.current; // abaikan event dari utterance lama yang di-cancel
    isSpeechSynthesisSpeaking.current = true;
    setIsSpeaking(true);

    const utterance = new SpeechSynthesisUtterance(textUtama);
    utterance.lang = 'id-ID';

    let sudah = false;
    const habis = () => {
      if (sudah || id !== utteranceId.current) return;
      sudah = true;
      isSpeechSynthesisSpeaking.current = false;
      setIsSpeaking(false);
      if (nextStateDelay) nanti(() => pindah(nextStateDelay), 1000);
      if (selesai) selesai();
    };

    utterance.onend = habis;
    // Suara Indonesia tidak selalu ada di tiap perangkat. Kalau gagal, onerror
    // harus tetap melanjutkan alur - kalau tidak, pengguna tunanetra terjebak.
    utterance.onerror = habis;

    window.speechSynthesis.speak(utterance);

    // PENJAGA WAKTU. Seluruh alur bergantung pada onend, dan onend TIDAK SELALU
    // BERBUNYI: cancel() yang langsung disusul speak() kadang membuat ucapan baru
    // ditelan peramban (terbukti saat menguji tombol Keluar - tanpa penjaga ini
    // aplikasinya tidak pernah menutup). Kalau itu terjadi, alur harus tetap jalan;
    // pengguna tunanetra tidak bisa melihat bahwa sistemnya menggantung.
    // ponytail: perkiraan kasar dari jumlah kata, bukan pengukuran durasi suara.
    const perkiraanMs = 1800 + textUtama.trim().split(/\s+/).length * 420;
    const penjaga = () => {
      if (sudah) return;
      // Masih benar-benar bicara (perkiraannya terlalu pendek) -> tunggu, jangan
      // potong di tengah kalimat. Yang dipaksa lanjut hanya ucapan yang ditelan.
      if (window.speechSynthesis?.speaking) { nanti(penjaga, 1500); return; }
      habis();
    };
    nanti(penjaga, perkiraanMs);
  };

  const peringatkan = (pesan, aksiBerikutnya) => {
    const teksPeringatan = `${pesan}. ${aksiBerikutnya}`;
    playSystemAudio(teksPeringatan);
  };

  // === MENDENGARKAN: mikrofon sungguhan + deteksi hening 3 detik (spec 4) ===
  // Mengisi nivRef supaya orb bergerak mengikuti suara asli pengguna - orb sudah
  // mendukungnya lewat prop levelRef, hanya belum pernah dialiri.
  // Selesai sendiri setelah HENING_MS tanpa suara di atas AMBANG_SUARA.
  // ponytail: analyser saja, belum merekam. MediaRecorder masuk di sini juga saat
  // disambungkan ke /api/tanya - tidak ada logika layar yang perlu berubah.
  const dengarkan = (saatSelesai) => {
    if (!navigator.mediaDevices?.getUserMedia) {
      peringatkan('Mikrofon tidak tersedia di perangkat ini',
                  'Kamu masih bisa mengetuk layar untuk memotret ulang.');
      return;
    }
    const gen = ++dengarGen.current;
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      // Pengguna bisa menyela SELAGI izin mikrofon masih diminta. Tanpa penjaga ini
      // sesinya tetap jalan lalu memindahkan state yang sudah tidak diinginkan -
      // pola yang sama dengan penjaga utteranceId di playSystemAudio.
      if (gen !== dengarGen.current) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const buf = new Float32Array(analyser.fftSize);

      let raf = 0;
      let diamSejak = performance.now();
      let hidup = true;

      const tutup = () => {
        if (!hidup) return;
        hidup = false;
        cancelAnimationFrame(raf);
        stream.getTracks().forEach((t) => t.stop());
        ctx.close().catch(() => {});
        nivRef.current = 0;
        hentiDengarRef.current = null;
      };

      // Dipanggil pindah(): pengguna menyela, jadi jangan lanjutkan alur lama.
      hentiDengarRef.current = tutup;

      const tik = () => {
        analyser.getFloatTimeDomainData(buf);
        let jml = 0;
        for (let i = 0; i < buf.length; i++) jml += buf[i] * buf[i];
        const rms = Math.sqrt(jml / buf.length);
        nivRef.current = Math.min(1, rms * 8);

        const now = performance.now();
        if (rms > AMBANG_SUARA) {
          diamSejak = now;
          aktifRef.current = now;      // suara juga menunda penutupan otomatis (spec 7)
        }
        if (now - diamSejak >= HENING_MS) {
          tutup();
          if (gen === dengarGen.current) saatSelesai();
          return;
        }
        raf = requestAnimationFrame(tik);
      };
      tik();
    }).catch(() => {
      peringatkan('Mikrofon belum diizinkan',
                  'Buka pengaturan izin situs di peramban, nyalakan mikrofon, lalu ketuk layar lagi.');
    });
  };

  // === SEAM BACKEND ===
  // ponytail: dua fungsi ini adalah satu-satunya tempat yang perlu diganti saat
  // disambungkan ke server - jadi POST /api/foto dan POST /api/tanya. Layar sudah
  // menunggu PROMISE, bukan timer, jadi durasinya otomatis mengikuti proses nyata.
  const jeda = (ms) => new Promise((r) => { timersRef.current.push(setTimeout(r, ms)); });
  const kirimFoto = async () => { await jeda(1200); };
  const kirimPertanyaan = async () => {
    await jeda(1800);
    return 'Nominal uang ini adalah dua ribu rupiah.';
  };

  // === KAMERA ===
  // Menyalakan kamera sesuai arah (depan/belakang). Stream lama dimatikan dulu,
  // karena banyak HP tidak bisa membuka dua kamera sekaligus.
  // exact = true dipakai saat flip, supaya gagal (dan kita beri tahu user) kalau kamera itu tidak ada.
  const startStream = async (facing, exact = false) => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: exact ? { exact: facing } : { ideal: facing },
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      }
    });
    streamRef.current = stream;
    if (videoRef.current) videoRef.current.srcObject = stream;
    return stream;
  };

  // Matikan kamera saat halaman ditutup
  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // === EFFECTS BERDASARKAN STATE ===
  useEffect(() => {
    if (appState === 'INIT') {
      let isMounted = true;
      setCapturedImage(null);

      startStream(facingRef.current)
        .then(() => {
          if (isMounted) {
            pindah('CAMERA_READY');
            playSystemAudio("Selamat datang di SayIt. Silakan arahkan kamera, lalu ketuk layar untuk memotret.");
          }
        })
        .catch(err => {
          console.error(err);
          peringatkan("Kamera tidak ditemukan", "Periksa izin kamera.");
        });

      return () => { isMounted = false; };
    }
  }, [appState]);

  useEffect(() => {
    if (appState === 'LISTENING_Q') {
      dengarkan(() => pindah('PROCESSING_Q'));
    }
  }, [appState]);

  // Spec 3: orb berputar selama prosesnya BERJALAN, bukan selama durasi tetap.
  // Pindah layar terjadi saat promise selesai - tidak ada timeout simulasi lagi.
  useEffect(() => {
    if (appState !== 'PROCESSING_Q') return;
    let batal = false;
    playSystemAudio('Sedang memproses pertanyaan Anda.');
    kirimPertanyaan()
      .then((jawab) => {
        if (batal) return;
        setResultText(jawab);
        pindah('SHOWING_RESULT');
      })
      .catch(() => {
        if (batal) return;
        peringatkan('Tidak bisa menghubungi server SayIt',
                    'Periksa koneksi internetmu, lalu ketuk layar untuk memotret lagi.');
        pindah('INIT');
      });
    return () => { batal = true; };
  }, [appState]);

  useEffect(() => {
    if (appState === 'SHOWING_RESULT') {
      playSystemAudio(resultText, 'PROMPTING_MENU');
    }
  }, [appState, resultText]);

  useEffect(() => {
    if (appState === 'PROMPTING_MENU') {
      playSystemAudio("Katakan Ulangi untuk pembacaan ulang, Foto Lagi untuk memotret kembali, atau Keluar untuk menutup aplikasi.", 'LISTENING_MENU');
    }
  }, [appState]);

  useEffect(() => {
    if (appState === 'LISTENING_MENU') {
      // ponytail: jawaban menu belum dikenali (butuh STT dari backend), jadi hening
      // 3 detik berarti pengguna tidak menjawab -> diam di layar hasil, bukan
      // memotret ulang diam-diam. Timer idle 30 detik yang menutup aplikasinya.
      // HASIL_SUNYI, bukan SHOWING_RESULT: yang kedua membacakan ulang lalu kembali
      // ke menu lagi - lingkaran suara tanpa akhir.
      dengarkan(() => pindah('HASIL_SUNYI'));
    }
  }, [appState]);

  // === UKUR RUANG ORB DI LAYAR HASIL (menyesuaikan tinggi card output) ===
  useEffect(() => {
    const el = orbSlotRef.current;
    if (!el) return;
    const update = () => {
      const top = el.offsetTop + el.offsetHeight / 2;
      const scale = Math.min(0.9, Math.max(0.6, el.offsetHeight / 240));
      setOrbSlot((prev) =>
        prev.top !== null && Math.abs(prev.top - top) < 1 && Math.abs(prev.scale - scale) < 0.01
          ? prev
          : { top, scale }
      );
    };
    update();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(update) : null;
    if (ro) ro.observe(el);
    window.addEventListener('resize', update);
    return () => {
      if (ro) ro.disconnect();
      window.removeEventListener('resize', update);
    };
  }, [resultText]);

  // Lanjut ke tahap membaca foto (dipakai oleh jepretan kamera maupun foto upload)
  // Spec 3: menunggu promise, bukan timeout. Orb berputar selama prosesnya jalan.
  const proceedWithPhoto = async (imageUrl, mirrored) => {
    setCapturedImage(imageUrl);
    setCapturedMirror(mirrored);
    pindah('PROCESSING_VISION');
    playSystemAudio('Sedang membaca foto.');

    try {
      await kirimFoto(imageUrl);
    } catch {
      peringatkan('Foto tidak bisa diproses', 'Ketuk layar untuk memotret ulang.');
      pindah('INIT');
      return;
    }
    pindah('PROMPTING_Q');
    playSystemAudio('Apa yang ingin anda tanyakan dari foto ini?', 'LISTENING_Q');
  };

  /** Matikan kamera dan semua suara. Dipakai saat keluar dan saat idle. */
  const matikanSemua = () => {
    bersihkanTimer();
    if (hentiDengarRef.current) hentiDengarRef.current();
    hentikanSuara();
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  };

  /** Tutup aplikasi (spec 6 dan 7).
   *
   *  Halaman web TIDAK BISA menutup dirinya sendiri kecuali dibuka oleh skrip.
   *  Di PWA terpasang (manifest display: standalone) window.close() diizinkan dan
   *  benar-benar menutup. Di tab peramban biasa ia gagal DIAM-DIAM - jadi harus ada
   *  layar akhir yang jelas dan terucap, bukan layar putih kosong seperti state
   *  'IDLE' yang lama. */
  const tutupAplikasi = () => {
    matikanSemua();
    setAppState('SELESAI');
    window.close();
  };

  // Spec 6: ucapkan terima kasih, lalu tutup - tanpa layar perantara.
  const keluar = () => {
    bersihkanTimer();
    if (hentiDengarRef.current) hentiDengarRef.current();
    setAppState('SELESAI');
    playSystemAudio('Terima kasih sudah memakai aplikasi kami.', null, tutupAplikasi);
  };

  // Spec 7: di layar hasil, 30 detik tanpa interaksi apa pun -> tutup aplikasi.
  // Diperiksa dengan interval, bukan timeout, supaya DUA sumber aktivitas bisa
  // menundanya: sentuhan/tombol di sini, dan suara pengguna dari dengarkan().
  useEffect(() => {
    if (!isResultScreen) return;
    const sentuh = () => { aktifRef.current = performance.now(); };
    sentuh();
    ['pointerdown', 'keydown'].forEach((e) => window.addEventListener(e, sentuh, true));
    const iv = setInterval(() => {
      if (performance.now() - aktifRef.current >= IDLE_MS) {
        clearInterval(iv);
        tutupAplikasi();
      }
    }, 1000);
    return () => {
      clearInterval(iv);
      ['pointerdown', 'keydown'].forEach((e) => window.removeEventListener(e, sentuh, true));
    };
  }, [isResultScreen]);

  // Tombol flip: ganti kamera depan <-> belakang
  const handleFlip = async (e) => {
    e.stopPropagation(); // jangan ikut memicu "ketuk layar untuk memotret"
    if (appState !== 'CAMERA_READY' || isFlipping.current) return;
    aktifRef.current = performance.now();
    hentikanSuara();                     // spec 2: tombol menyela ucapan sistem
    isFlipping.current = true;

    const prev = facingRef.current;
    const next = prev === 'user' ? 'environment' : 'user';
    try {
      await startStream(next, true);
      facingRef.current = next;
      setFacingMode(next);
      playSystemAudio(next === 'environment' ? "Kamera belakang aktif." : "Kamera depan aktif.");
    } catch (err) {
      console.error(err);
      try { await startStream(prev); } catch (err2) { console.error(err2); }
      peringatkan("Kamera tidak dapat diganti", "Perangkat ini mungkin tidak memiliki kamera lain.");
    } finally {
      isFlipping.current = false;
    }
  };

  // Tombol upload: buka galeri/file perangkat
  const handleUploadClick = (e) => {
    e.stopPropagation();
    if (appState !== 'CAMERA_READY') return;
    aktifRef.current = performance.now();
    hentikanSuara();                     // spec 2: tombol menyela ucapan sistem
    if (fileInputRef.current) fileInputRef.current.click();
  };

  const handleFileChange = (e) => {
    e.stopPropagation();
    const file = e.target.files && e.target.files[0];
    e.target.value = ''; // supaya foto yang sama bisa dipilih lagi
    if (!file || appState !== 'CAMERA_READY') return;

    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      // Perkecil kalau sangat besar (maks 1600px) supaya ringan, dan orientasi EXIF ikut dirapikan
      const maxSide = 1600;
      const sc = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
      const c = document.createElement('canvas');
      c.width = Math.round(img.naturalWidth * sc);
      c.height = Math.round(img.naturalHeight * sc);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      proceedWithPhoto(c.toDataURL('image/jpeg', 0.9), false);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      peringatkan("Foto tidak dapat dibuka", "Silakan pilih foto lain.");
    };
    img.src = url;
  };

  // === HANDLER KLIK ===
  const handleScreenClick = () => {
    // Spec 2 (barge-in): dulu di sini ada `if (isSpeechSynthesisSpeaking.current)
    // return;` yang memblokir SEMUA ketukan selagi sistem bicara - termasuk
    // sambutan yang panjang. Sekarang ketukan justru MENGHENTIKAN ucapan sistem.
    aktifRef.current = performance.now();
    hentikanSuara();

    if (appState === 'CAMERA_READY') {
      let imageUrl = null;
      if (videoRef.current) {
        const video = videoRef.current;
        const vw = video.videoWidth;
        const vh = video.videoHeight;
        const W = window.innerWidth;
        const H = window.innerHeight;
        
        const scale = Math.max(W / vw, H / vh);
        const drawW = vw * scale;
        const drawH = vh * scale;
        const dx = (W - drawW) / 2;
        const dy = (H - drawH) / 2;

        const frameX = 24;
        const frameY = 60;
        const frameW = W - 48; 
        const frameH = H - 210; 

        const cropX = Math.max(0, (frameX - dx) / scale);
        const cropY = Math.max(0, (frameY - dy) / scale);
        const cropW = Math.min(vw - cropX, frameW / scale);
        const cropH = Math.min(vh - cropY, frameH / scale);

        const canvas = document.createElement('canvas');
        canvas.width = frameW;
        canvas.height = frameH;
        const ctx = canvas.getContext('2d');
        
        ctx.drawImage(video, cropX, cropY, cropW, cropH, 0, 0, frameW, frameH);
        
        imageUrl = canvas.toDataURL('image/jpeg');
      }

      proceedWithPhoto(imageUrl, facingRef.current === 'user');
    }
  };

  // === LOGIKA POSISI DAN VISIBILITAS TRANSISI KELOMPOK SCREEN ===

  // Mode AI orb: user input suara > sistem berbicara > diam
  const isListeningState = appState === 'LISTENING_Q' || appState === 'LISTENING_MENU';
  const orbMode = isListeningState ? 'listening' : isSpeaking ? 'speaking' : 'idle';

  // Posisi Orb untuk tiap layar
  let orbPosStyle = {
    position: 'absolute',
    left: '50%',
    transition: 'top 0.8s cubic-bezier(0.4, 0, 0.2, 1), transform 0.8s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.6s ease-in-out',
    zIndex: 35,
    pointerEvents: 'none'
  };

  if (isCamera) {
    orbPosStyle = {
      ...orbPosStyle,
      top: '50%',
      transform: 'translate(-50%, -50%) scale(0.3)',
      opacity: 0,
    };
  } else if (isProcessing) {
    orbPosStyle = {
      ...orbPosStyle,
      top: '50%',
      transform: 'translate(-50%, -50%) scale(1.1)',
      opacity: 1,
    };
  } else if (isQuestionScreen) {
    orbPosStyle = {
      ...orbPosStyle,
      top: '86%', 
      transform: 'translate(-50%, -50%) scale(0.9)',
      opacity: 1,
    };
  } else if (isResultScreen) {
    // Orb mengikuti ruang kosong antara foto dan card output (diukur otomatis)
    orbPosStyle = {
      ...orbPosStyle,
      top: orbSlot.top !== null ? `${orbSlot.top}px` : '59%',
      transform: `translate(-50%, -50%) scale(${orbSlot.scale})`,
      opacity: 1,
    };
  }

  // Elemen foto hasil jepretan (dipakai di layar pertanyaan & layar hasil)
  const photoImg = capturedImage ? (
    <img
      src={capturedImage}
      alt="Hasil Foto"
      style={{
        height: '100%',
        width: 'auto',
        maxWidth: '80%',
        objectFit: 'contain',
        borderRadius: '16px',
        transform: capturedMirror ? 'scaleX(-1)' : 'none',
        boxShadow: '0 10px 30px rgba(0,0,0,0.1)'
      }}
    />
  ) : null;

  return (
    <main 
      onClick={handleScreenClick}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'white', 
        overflow: 'hidden',
        userSelect: 'none'
      }}
    >
      {/* CSS TOMBOL ICON */}
      <style dangerouslySetInnerHTML={{__html: `
        .btn-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          flex: 1;
          height: 52px;
          background-color: rgba(249, 115, 22, 0.18);
          color: #ea580c;
          border: none; 
          border-radius: 16px;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .btn-icon:hover {
          background-color: var(--jingga, #f97316); 
          color: white; 
        }
        .btn-icon:active {
          transform: scale(0.92); 
        }
        .btn-icon svg {
          width: 26px;
          height: 26px;
        }
        .btn-cam {
          pointer-events: auto;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 56px;
          height: 56px;
          padding: 0;
          border: none;
          border-radius: 50%;
          background-color: rgba(255, 255, 255, 0.92);
          color: #ea580c;
          box-shadow: 0 4px 10px rgba(0,0,0,0.35);
          cursor: pointer;
          transition: transform 0.2s ease, background-color 0.2s ease;
          -webkit-tap-highlight-color: transparent;
        }
        .btn-cam:active {
          transform: scale(0.92);
        }
        .btn-cam svg {
          width: 26px;
          height: 26px;
        }
      `}} />

      {/* Pembaca Layar Wajib (SR) */}
      <div aria-live="assertive" aria-atomic="true">
        <p className="sr">{srText}</p>
      </div>

      {/* Input file tersembunyi untuk tombol upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        onClick={(e) => e.stopPropagation()}
        style={{ display: 'none' }}
      />

      {/* Layer Kamera */}
      <video 
        ref={videoRef} 
        autoPlay 
        playsInline
        muted 
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover', 
          transform: facingMode === 'user' ? 'scaleX(-1)' : 'none', 
          zIndex: 0
        }}
      />

      {/* === SCREEN 1: UI KAMERA === */}
      {appState === 'CAMERA_READY' && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 20, pointerEvents: 'none', overflow: 'hidden' }}>
          <div style={{ 
            position: 'absolute', top: '60px', bottom: '150px', left: '24px', right: '24px', 
            boxShadow: '0 0 0 9999px rgba(0,0,0,0.3)' 
          }}>
            <div style={{ position: 'absolute', top: 0, left: 0, width: '40px', height: '40px', borderTop: '6px solid var(--jingga, #f97316)', borderLeft: '6px solid var(--jingga, #f97316)' }}></div>
            <div style={{ position: 'absolute', top: 0, right: 0, width: '40px', height: '40px', borderTop: '6px solid var(--jingga, #f97316)', borderRight: '6px solid var(--jingga, #f97316)' }}></div>
            <div style={{ position: 'absolute', bottom: 0, left: 0, width: '40px', height: '40px', borderBottom: '6px solid var(--jingga, #f97316)', borderLeft: '6px solid var(--jingga, #f97316)' }}></div>
            <div style={{ position: 'absolute', bottom: 0, right: 0, width: '40px', height: '40px', borderBottom: '6px solid var(--jingga, #f97316)', borderRight: '6px solid var(--jingga, #f97316)' }}></div>
          </div>

          {/* Baris bawah: upload (kiri) - shutter (tengah) - flip kamera (kanan) */}
          <div style={{ position: 'absolute', bottom: '40px', left: 0, right: 0, height: '76px', padding: '0 10.5%', boxSizing: 'border-box', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <button className="btn-cam" onClick={handleUploadClick} aria-label="Unggah foto dari perangkat">
              <svg fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </button>

            <div style={{ width: '76px', height: '76px', backgroundColor: 'white', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 10px rgba(0,0,0,0.5)' }}>
              <div style={{ width: '60px', height: '60px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '50%' }}></div>
            </div>

            <button className="btn-cam" onClick={handleFlip} aria-label="Balik kamera depan dan belakang">
              {/* Bentuk "switch-camera" dari Lucide (MIT), bukan gambaran sendiri:
                  badan kamera terbelah + lensa + dua chevron arah. Dua panah lurus
                  yang lama terbaca sebagai "tukar" apa saja, tidak spesifik kamera.
                  Busur buatan tangan sempat dicoba dan gagal - pada strokeWidth 2.5
                  kepala panahnya menyatu dengan busur jadi gumpalan di 46 px. */}
              <svg fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 19H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5"/>
                <path d="M13 5h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-5"/>
                <circle cx="12" cy="12" r="3"/>
                <path d="m18 22-3-3 3-3"/>
                <path d="m6 2 3 3-3 3"/>
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* === LOGO SAYIT (tampil di semua screen, tengah atas) === */}
      {/* Di screen kamera/pertanyaan/hasil: di atas (ukuran normal). Saat orb di tengah (memproses): turun ke tepat di atas orb dan membesar 2x, lalu kembali naik & mengecil saat ganti screen */}
      <div style={{
        position: 'absolute',
        top: '14px',
        left: '50%',
        transform: `translate(-50%, ${isProcessing ? 'calc(50vh - 204px)' : '0px'}) scale(${isProcessing ? 2 : 1})`,
        transformOrigin: '50% 100%', // membesar ke atas, jarak ke orb tetap
        transition: 'transform 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
        filter: 'drop-shadow(0 0 3px rgba(255,255,255,0.85))', // biar teks tetap terbaca di atas video kamera
        zIndex: 40,
        pointerEvents: 'none'
      }}>
        <SayItLogo />
      </div>

      {/* === PERSISTENT AI VOICE ORB (Untuk Screen Loading/Pertanyaan) === */}
      <div style={orbPosStyle}>
        <AiParticleOrb width={260} height={260} mode={orbMode} levelRef={nivRef} />
      </div>

      {/* === OVERLAY PUTIH UTAMA DENGAN TRANSISI HALUS === */}
      <div 
        style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'white',
          zIndex: 30,
          opacity: isCamera ? 0 : 1,
          pointerEvents: isCamera ? 'none' : 'auto',
          transition: 'opacity 0.8s ease-in-out',
          overflow: 'hidden'
        }}
      >
        {/* === SCREEN 3: HASIL FOTO & PERTANYAAN === */}
        <div 
          style={{
            position: 'absolute',
            inset: 0,
            opacity: isQuestionScreen ? 1 : 0,
            pointerEvents: isQuestionScreen ? 'auto' : 'none',
            transition: 'opacity 0.6s ease-in-out, transform 0.6s ease-in-out',
            transform: isQuestionScreen ? 'scale(1)' : 'scale(0.96)',
            zIndex: 31
          }}
        >
          {/* Foto besar di atas, sejajar dengan posisi foto di layar hasil (ukuran tetap 52% tinggi layar) */}
          <div style={{ position: 'absolute', top: 'max(5.5vh, 64px)', height: '52%', left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
            {photoImg}
          </div>
          
          {/* Teks pertanyaan di bawah foto, orb ada di bawah teks (86%) */}
          <h2 style={{ position: 'absolute', top: '66%', left: '24px', right: '24px', margin: 0, fontSize: '19px', fontWeight: '800', textAlign: 'center', color: 'black', lineHeight: 1.3 }}>
            Apa yang ingin anda tanyakan<br/>dari foto ini?
          </h2>
        </div>

        {/* === SCREEN 5: LAYAR HASIL AKHIR (foto -> orb -> output -> 3 tombol) === */}
        {/* Susunan flex: card output tumbuh sesuai panjang teks, ruang orb mengecil otomatis */}
        <div 
          style={{
            position: 'absolute',
            inset: 0,
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            paddingTop: 'max(5.5vh, 64px)', // sisakan ruang untuk logo di atas
            paddingBottom: '10vh',
            opacity: isResultScreen ? 1 : 0,
            pointerEvents: isResultScreen ? 'auto' : 'none',
            transition: 'opacity 0.6s ease-in-out, transform 0.6s ease-in-out',
            transform: isResultScreen ? 'scale(1)' : 'scale(0.96)',
            zIndex: 31
          }}
        >
          {/* 1. FOTO (ukuran normal 42vh, mengecil kalau teks output sangat panjang) */}
          <div style={{ flex: '0 1 42vh', minHeight: '18vh', width: '100%', display: 'flex', justifyContent: 'center' }}>
            {photoImg}
          </div>

          {/* 2. RUANG ORB: orb global diposisikan di tengah area ini */}
          <div ref={orbSlotRef} style={{ flex: '1 0 150px', width: '100%' }} />

          {/* 3. CARD OUTPUT: tinggi mengikuti teks, scroll kalau lebih dari 40vh */}
          <div style={{
            width: '75%',
            boxSizing: 'border-box',
            flex: '0 0 auto',
            minHeight: '10vh',
            maxHeight: '40vh',
            overflowY: 'auto',
            display: 'flex',
            padding: '14px 18px',
            backgroundColor: 'var(--jingga, #f97316)',
            borderRadius: '16px',
            boxShadow: '0 4px 20px rgba(249,115,22,0.2)'
          }}>
            <h2 style={{ width: '100%', margin: 'auto 0', fontSize: '15px', fontWeight: '700', textAlign: 'center', color: 'white', lineHeight: '1.5', overflowWrap: 'anywhere' }}>
              {resultText}
            </h2>
          </div>

          {/* 4. TIGA TOMBOL ICON */}
          {/* stopPropagation WAJIB di sini. Latar layar hasil sengaja dibiarkan
              menembus ke handleScreenClick supaya ketukan di mana saja bisa menyela
              ucapan (spec 2) - tetapi klik tombol tidak boleh ikut naik ke sana:
              handleScreenClick memanggil hentikanSuara(), yang menaikkan utteranceId
              dan membuat callback "selesai" milik tombol Keluar dianggap kedaluwarsa,
              sehingga aplikasinya tidak pernah menutup. Terbukti saat diuji. */}
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ width: '75%', display: 'flex', gap: '12px', marginTop: '24px', flex: '0 0 auto' }}
          >
            <button 
              className="btn-icon"
              onClick={() => {
                // setAppState('SHOWING_RESULT') tidak berbuat apa pun kalau state-nya
                // SUDAH itu - React mengabaikan set ke nilai yang sama, jadi
                // pembacaan tidak pernah terulang. Diucapkan langsung saja.
                aktifRef.current = performance.now();
                bersihkanTimer();
                if (hentiDengarRef.current) hentiDengarRef.current();
                playSystemAudio(resultText, 'PROMPTING_MENU');
              }}
              aria-label="Ulangi Pembacaan"
            >
              <svg fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>
                <path d="M21 3v5h-5"/>
              </svg>
            </button>

            <button 
              className="btn-icon"
              onClick={() => { hentikanSuara(); pindah('INIT'); }}
              aria-label="Foto Lagi"
            >
              <svg fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" strokeLinecap="round" strokeLinejoin="round">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                <circle cx="12" cy="13" r="4"/>
              </svg>
            </button>

            <button 
              className="btn-icon"
              onClick={keluar}
              aria-label="Keluar Aplikasi"
            >
              <svg fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* === LAYAR SELESAI ===
          window.close() hanya berhasil di PWA terpasang. Di tab peramban biasa ia
          gagal diam-diam, jadi inilah yang terlihat - layar akhir yang jelas dan
          terucap, bukan layar putih kosong seperti state 'IDLE' yang lama. */}
      {appState === 'SELESAI' && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 60,
          background: 'var(--hitam, #050809)', color: 'var(--putih, #fafafa)',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: '26px', padding: '0 32px', textAlign: 'center'
        }}>
          <SayItLogo height={44} />
          <p style={{ fontSize: '19px', fontWeight: 700, lineHeight: 1.4, margin: 0 }}>
            Terima kasih sudah memakai SayIt.
          </p>
          <p style={{ fontSize: '15px', color: 'var(--abu, #8b9196)', margin: 0 }}>
            Aplikasi sudah ditutup. Kamu bisa menutup tab ini.
          </p>
          <button
            className="btn-icon"
            style={{ width: 'auto', padding: '14px 26px', fontSize: '16px', fontWeight: 700 }}
            onClick={() => { aktifRef.current = performance.now(); pindah('INIT'); }}
          >
            Mulai lagi
          </button>
        </div>
      )}
    </main>
  );
}
