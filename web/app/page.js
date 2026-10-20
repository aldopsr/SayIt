'use client';

import { useState, useEffect, useRef } from 'react';

// === KOMPONEN AI ORB (PARTIKEL 3D + BATANG FREKUENSI MELINGKAR) ===
// Bola di tengah dikelilingi batang-batang frekuensi (ujung membulat) yang memanjang-memendek mengikuti suara.
// mode:
//  - 'idle'      : tidak ada suara -> batang hilang, bola tenang bernapas pelan
//  - 'speaking'  : sistem sedang berbicara -> batang bergerak halus, lobus berputar pelan, oranye
//  - 'listening' : user sedang input suara -> batang lebih liar/cepat naik-turun, oranye-merah pekat, bola mengerut
// levelRef (opsional): ref berisi angka 0..1 dari volume mic asli untuk mode 'listening'.
//   Kalau tidak diisi, amplitudo suara user disimulasikan.
const ORB_MODES = {
  idle:      { amp: 0.05, speed: 0.4, bars: 0, glow: 0.22, radius: 1.0,  pulse: 0.02, mix: 0, r: 251, g: 140, b: 50 },
  speaking:  { amp: 0.12, speed: 1.4, bars: 1, glow: 0.4,  radius: 1.03, pulse: 0.06, mix: 0, r: 249, g: 115, b: 22 },
  listening: { amp: 0.14, speed: 2.0, bars: 1, glow: 0.45, radius: 0.95, pulse: 0.05, mix: 1, r: 225, g: 70,  b: 12 },
};

const BAR_COUNT = 56;

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

    // Karakter tiap batang (tetap): kecepatan & fase sendiri supaya panjangnya tidak seragam
    const rnd = (n) => { const x = Math.sin(n * 12.9898) * 43758.5453; return x - Math.floor(x); };
    const bars = [];
    for (let i = 0; i < BAR_COUNT; i++) {
      bars.push({ ang: (i / BAR_COUNT) * Math.PI * 2 - Math.PI / 2, f: 3 + rnd(i + 1) * 6, p: rnd(i + 99) * Math.PI * 2, h: 0 });
    }

    const R = width * 0.235;
    const cx = width / 2;
    const cy = height / 2;
    const fov = 260;
    const maxLen = R * 0.75;
    const barWidth = 4.5;

    const lerp = (a, b, t) => a + (b - a) * t;
    const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

    const cur = { ...ORB_MODES.idle }; // nilai yang dihaluskan antar mode
    let spin = 0, wave = 0, wt = 0, time = 0, env = 0;
    let last = performance.now();
    let raf;

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

      ctx.clearRect(0, 0, width, height);

      // Glow lembut di belakang bola
      const grad = ctx.createRadialGradient(cx, cy, R * 0.2, cx, cy, width / 2);
      grad.addColorStop(0, colStr(cur.glow * (0.4 + 0.6 * env)));
      grad.addColorStop(1, colStr(0));
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, width, height);

      // Partikel bola
      const baseR = R * cur.radius * (1 + cur.pulse * env * 2);
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

      // Batang frekuensi melingkar di sekeliling bola (ujung membulat)
      if (cur.bars > 0.02) {
        const r0 = baseR * (1 + cur.amp) + 8;
        const follow = 1 - Math.exp(-dt * lerp(10, 24, cur.mix)); // listening: lebih responsif
        const sp = 1 + 1.2 * cur.mix;
        ctx.lineCap = 'round';
        ctx.lineWidth = barWidth;

        for (const bar of bars) {
          const jit = Math.abs(Math.sin(time * bar.f * sp + bar.p));
          const lobeS = 0.5 + 0.5 * Math.sin(bar.ang * 3 + wt * 1.6); // speaking: lobus berputar pelan
          const lobeL = 0.5 + 0.5 * Math.sin(bar.ang * 7 - wt * 2.4); // listening: lebih acak
          const lobe = lobeS + (lobeL - lobeS) * cur.mix;
          const t = Math.pow(0.15 + 0.85 * (0.55 * jit + 0.45 * lobe), 1.5);
          const targetH = t * (0.2 + 0.8 * env);
          bar.h += (targetH - bar.h) * follow;

          const len = 1 + bar.h * maxLen * cur.bars;
          const cos = Math.cos(bar.ang), sin = Math.sin(bar.ang);
          ctx.strokeStyle = colStr((0.55 + 0.45 * bar.h) * cur.bars);
          ctx.beginPath();
          ctx.moveTo(cx + cos * r0, cy + sin * r0);
          ctx.lineTo(cx + cos * (r0 + len), cy + sin * (r0 + len));
          ctx.stroke();
        }
      }

      raf = requestAnimationFrame(render);
    };

    raf = requestAnimationFrame(render);
    return () => cancelAnimationFrame(raf);
  }, [width, height, levelRef]);

  return <canvas ref={canvasRef} style={{ display: 'block', width, height }} />;
}

export default function SayItPage() {
  // === STATE MANAGEMENT ===
  const [appState, setAppState] = useState('INIT');
  const [srText, setSrText] = useState('');
  const [resultText, setResultText] = useState('');
  const [capturedImage, setCapturedImage] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false); // sistem sedang berbicara (TTS)
  const [orbSlot, setOrbSlot] = useState({ top: null, scale: 0.9 }); // posisi orb di layar hasil

  // === REFS ===
  const videoRef = useRef(null);
  const isSpeechSynthesisSpeaking = useRef(false);
  const utteranceId = useRef(0);
  const orbSlotRef = useRef(null);

  // === FUNGSI UTILITAS: AUDIO & AKSESIBILITAS ===
  const playSystemAudio = (textUtama, nextStateDelay = null) => {
    setSrText(textUtama);
    
    window.speechSynthesis.cancel();
    const id = ++utteranceId.current; // abaikan event dari utterance lama yang di-cancel
    isSpeechSynthesisSpeaking.current = true;
    setIsSpeaking(true);

    const utterance = new SpeechSynthesisUtterance(textUtama);
    utterance.lang = 'id-ID';
    
    utterance.onend = () => {
      if (id !== utteranceId.current) return;
      isSpeechSynthesisSpeaking.current = false;
      setIsSpeaking(false);
      if (nextStateDelay) {
        setTimeout(() => {
          setAppState(nextStateDelay);
        }, 1000); 
      }
    };
    
    utterance.onerror = () => {
      if (id !== utteranceId.current) return;
      isSpeechSynthesisSpeaking.current = false;
      setIsSpeaking(false);
    };

    window.speechSynthesis.speak(utterance);
  };

  const peringatkan = (pesan, aksiBerikutnya) => {
    const teksPeringatan = `${pesan}. ${aksiBerikutnya}`;
    playSystemAudio(teksPeringatan);
  };

  // === MEKANISME SIMULASI MENDENGARKAN (UI MOCK MODE) ===
  const startListening = (onSilenceCallback) => {
    setTimeout(() => {
      onSilenceCallback();
    }, 3000);
  };

  // === EFFECTS BERDASARKAN STATE ===
  useEffect(() => {
    if (appState === 'INIT') {
      let isMounted = true;
      setCapturedImage(null);
      
      const constraints = {
        video: {
          facingMode: 'user', 
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      };

      navigator.mediaDevices.getUserMedia(constraints)
        .then(stream => {
          if (isMounted && videoRef.current) {
            videoRef.current.srcObject = stream;
            setAppState('CAMERA_READY');
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
      startListening(() => {
        setAppState('PROCESSING_Q');
      });
    }
  }, [appState]);

  useEffect(() => {
    if (appState === 'PROCESSING_Q') {
      playSystemAudio("Sedang memproses pertanyaan Anda.");
      setTimeout(() => {
        setResultText("Nominal uang ini adalah dua ribu rupiah.");
        setAppState('SHOWING_RESULT');
      }, 3000); 
    }
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
      startListening(() => {
        setAppState('INIT'); 
      });
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

  // === HANDLER KLIK ===
  const handleScreenClick = () => {
    if (isSpeechSynthesisSpeaking.current) return;

    if (appState === 'CAMERA_READY') {
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
        
        const imageUrl = canvas.toDataURL('image/jpeg');
        setCapturedImage(imageUrl);
      }

      setAppState('PROCESSING_VISION');
      playSystemAudio("Sedang membaca foto.");
      
      setTimeout(() => {
        setAppState('PROMPTING_Q');
        playSystemAudio("Apa yang ingin anda tanyakan dari foto ini?", 'LISTENING_Q');
      }, 3000);
    }
  };

  // === LOGIKA POSISI DAN VISIBILITAS TRANSISI KELOMPOK SCREEN ===
  const isCamera = appState === 'INIT' || appState === 'CAMERA_READY';
  const isProcessing = appState === 'PROCESSING_VISION' || appState === 'PROCESSING_Q';
  const isQuestionScreen = appState === 'PROMPTING_Q' || appState === 'LISTENING_Q';
  const isResultScreen = appState === 'SHOWING_RESULT' || appState === 'PROMPTING_MENU' || appState === 'LISTENING_MENU';

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
        transform: 'scaleX(-1)',
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
      `}} />

      {/* Pembaca Layar Wajib (SR) */}
      <div aria-live="assertive" aria-atomic="true">
        <p className="sr">{srText}</p>
      </div>

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
          transform: 'scaleX(-1)', 
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

          <div style={{ position: 'absolute', bottom: '40px', left: '50%', transform: 'translateX(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ width: '76px', height: '76px', backgroundColor: 'white', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 10px rgba(0,0,0,0.5)' }}>
              <div style={{ width: '60px', height: '60px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '50%' }}></div>
            </div>
          </div>
        </div>
      )}

      {/* === PERSISTENT AI VOICE ORB (Untuk Screen Loading/Pertanyaan) === */}
      <div style={orbPosStyle}>
        <AiParticleOrb width={260} height={260} mode={orbMode} />
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
          {/* Foto besar di atas (10% - 62% layar) */}
          <div style={{ position: 'absolute', top: '10%', height: '52%', left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
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
            paddingTop: '5.5vh',
            paddingBottom: '10vh',
            opacity: isResultScreen ? 1 : 0,
            pointerEvents: isResultScreen ? 'auto' : 'none',
            transition: 'opacity 0.6s ease-in-out, transform 0.6s ease-in-out',
            transform: isResultScreen ? 'scale(1)' : 'scale(0.96)',
            zIndex: 31
          }}
          onClick={(e) => e.stopPropagation()} 
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
          <div style={{ width: '75%', display: 'flex', gap: '12px', marginTop: '24px', flex: '0 0 auto' }}>
            <button 
              className="btn-icon"
              onClick={() => setAppState('SHOWING_RESULT')}
              aria-label="Ulangi Pembacaan"
            >
              <svg fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>
                <path d="M21 3v5h-5"/>
              </svg>
            </button>

            <button 
              className="btn-icon"
              onClick={() => setAppState('INIT')}
              aria-label="Foto Lagi"
            >
              <svg fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" strokeLinecap="round" strokeLinejoin="round">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                <circle cx="12" cy="13" r="4"/>
              </svg>
            </button>

            <button 
              className="btn-icon"
              onClick={() => {
                playSystemAudio("Terima kasih sudah memakai aplikasi kami.");
                setAppState('IDLE');
              }}
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
    </main>
  );
}