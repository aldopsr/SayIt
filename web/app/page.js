'use client';

import { useState, useEffect, useRef } from 'react';

// === KOMPONEN BOLA PARTIKEL 3D REAKSIF SUARA (CANVAS AI ORB) ===
function AiParticleOrb({ width = 160, height = 160, isActive = true }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    const numParticles = 350;
    const particles = [];
    for (let i = 0; i < numParticles; i++) {
      const phi = Math.acos(-1 + (2 * i) / numParticles);
      const theta = Math.sqrt(numParticles * Math.PI) * phi;
      particles.push({
        x0: Math.cos(theta) * Math.sin(phi),
        y0: Math.sin(theta) * Math.sin(phi),
        z0: Math.cos(phi),
        phi,
        theta
      });
    }

    const baseRadius = width * 0.32;
    const cx = width / 2;
    const cy = height / 2;

    const render = (time) => {
      const t = time * 0.0006;
      ctx.clearRect(0, 0, width, height);

      const pitchModulation = isActive 
        ? Math.sin(t * 8) * 0.35 + Math.sin(t * 12) * 0.25 + Math.cos(t * 4.5) * 0.4 
        : Math.sin(t * 1.5) * 0.08;

      const currentAmp = baseRadius * (0.12 + Math.abs(pitchModulation) * 0.25);

      const projected = particles.map((p) => {
        const wave = Math.sin(p.phi * 4 + t * 5) * Math.cos(p.theta * 3 + t * 3.5);
        const pitchDisplacement = wave * currentAmp * (0.8 + Math.abs(p.y0 * 1.5));

        const r = baseRadius + pitchDisplacement;

        let x = p.x0 * r;
        let y = p.y0 * r;
        let z = p.z0 * r;

        const cosY = Math.cos(t * 0.5);
        const sinY = Math.sin(t * 0.5);
        let x1 = x * cosY - z * sinY;
        let z1 = x * sinY + z * cosY;

        const cosX = Math.cos(t * 0.3);
        const sinX = Math.sin(t * 0.3);
        let y2 = y * cosX - z1 * sinX;
        let z2 = y * sinX + z1 * cosX;

        const fov = 250;
        const scale = fov / (fov + z2 + baseRadius);
        const px = cx + x1 * scale;
        const py = cy + y2 * scale;

        return { px, py, z: z2, scale };
      });

      projected.sort((a, b) => a.z - b.z);

      projected.forEach((p) => {
        const alpha = Math.max(0.25, (p.z + baseRadius) / (baseRadius * 2.2));
        const particleSize = Math.max(0.7, p.scale * 1.6);

        if (p.z > 0) {
          ctx.fillStyle = `rgba(255, 255, 255, ${Math.min(1, alpha + 0.4)})`;
        } else {
          ctx.fillStyle = `rgba(249, 115, 22, ${alpha + 0.1})`;
        }

        ctx.beginPath();
        ctx.arc(p.px, p.py, particleSize, 0, Math.PI * 2);
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animationFrameId);
  }, [width, height, isActive]);

  return <canvas ref={canvasRef} width={width} height={height} style={{ display: 'block' }} />;
}

export default function SayItPage() {
  // === STATE MANAGEMENT ===
  const [appState, setAppState] = useState('INIT');
  const [srText, setSrText] = useState('');
  const [resultText, setResultText] = useState('');
  const [capturedImage, setCapturedImage] = useState(null);

  // === REFS ===
  const videoRef = useRef(null);
  const isSpeechSynthesisSpeaking = useRef(false);

  // === FUNGSI UTILITAS: AUDIO & AKSESIBILITAS ===
  const playSystemAudio = (textUtama, nextStateDelay = null) => {
    setSrText(textUtama);
    
    window.speechSynthesis.cancel();
    isSpeechSynthesisSpeaking.current = true;

    const utterance = new SpeechSynthesisUtterance(textUtama);
    utterance.lang = 'id-ID';
    
    utterance.onend = () => {
      isSpeechSynthesisSpeaking.current = false;
      if (nextStateDelay) {
        setTimeout(() => {
          setAppState(nextStateDelay);
        }, 1000); 
      }
    };
    
    utterance.onerror = () => {
        isSpeechSynthesisSpeaking.current = false;
    }

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

  // Kalkulasi Posisi AI Orb Berdasarkan State Layar
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
      top: '74%', 
      transform: 'translate(-50%, -50%) scale(0.9)',
      opacity: 1,
    };
  } else if (isResultScreen) {
    orbPosStyle = {
      ...orbPosStyle,
      top: '50%', 
      transform: 'translate(-50%, -50%) scale(0.8)',
      opacity: 0,
    };
  }

  const RenderCapturedPhoto = () => (
    <div style={{ width: '100%', display: 'flex', justifyContent: 'center', flexShrink: 0 }}>
      <img 
        src={capturedImage} 
        alt="Hasil Foto" 
        style={{ 
          maxWidth: '100%', 
          maxHeight: '44vh', 
          objectFit: 'contain', 
          borderRadius: '16px',
          transform: 'scaleX(-1)', 
          boxShadow: '0 10px 30px rgba(0,0,0,0.1)' 
        }} 
      />
    </div>
  );

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
      <style dangerouslySetInnerHTML={{__html: `
        .btn-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 60px;
          height: 60px;
          background-color: rgba(249, 115, 22, 0.2);
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
          width: 28px;
          height: 28px;
        }
      `}} />

      <div aria-live="assertive" aria-atomic="true">
        <p className="sr">{srText}</p>
      </div>

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

      <div style={orbPosStyle}>
        <AiParticleOrb width={180} height={180} isActive={true} />
      </div>

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
        {/* === SCREEN 3: PERTANYAAN === */}
        <div 
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '30px 24px 24px 24px', 
            opacity: isQuestionScreen ? 1 : 0,
            pointerEvents: isQuestionScreen ? 'auto' : 'none',
            transition: 'opacity 0.6s ease-in-out, transform 0.6s ease-in-out',
            transform: isQuestionScreen ? 'scale(1)' : 'scale(0.96)',
            zIndex: 31
          }}
        >
          {capturedImage && <RenderCapturedPhoto />}
          
          <h2 style={{ fontSize: '19px', fontWeight: '800', textAlign: 'center', color: 'black', marginTop: '20px' }}>
            Apa yang ingin anda tanyakan<br/>dari foto ini?
          </h2>
        </div>

        {/* === SCREEN 5: HASIL AKHIR (Jarak Flexbox Disamakan) === */}
        <div 
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '24px 24px 28px 24px',
            opacity: isResultScreen ? 1 : 0,
            pointerEvents: isResultScreen ? 'auto' : 'none',
            transition: 'opacity 0.6s ease-in-out, transform 0.6s ease-in-out',
            transform: isResultScreen ? 'scale(1)' : 'scale(0.96)',
            zIndex: 31
          }}
          onClick={(e) => e.stopPropagation()} 
        >
          {capturedImage && <RenderCapturedPhoto />}

          {/* AI Orb di tengah dengan ukuran flex yang memberikan jarak seragam atas dan bawah */}
          <div style={{ 
            flex: 1, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            transform: 'scale(0.75)',
            margin: '4px 0'
          }}>
             <AiParticleOrb width={180} height={180} isActive={true} />
          </div>

          {/* TEKS OUTPUT & TOMBOL ICON */}
          <div style={{ width: '100%', maxWidth: '600px', display: 'flex', flexDirection: 'column', gap: '14px', flexShrink: 0 }}>
            
            {/* Teks Output (Solid Orange) */}
            <div style={{ backgroundColor: 'var(--jingga, #f97316)', padding: '18px 20px', borderRadius: '16px', boxShadow: '0 4px 20px rgba(249,115,22,0.2)' }}>
              <h2 style={{ fontSize: '15px', fontWeight: '700', textAlign: 'center', color: 'white', margin: 0, lineHeight: '1.5' }}>
                {resultText}
              </h2>
            </div>
            
            {/* Tombol Icon Action (Horizontal) */}
            <div style={{ display: 'flex', justifyContent: 'space-evenly', alignItems: 'center', padding: '0 10px' }}>
              
              <button 
                className="btn-icon"
                onClick={() => setAppState('SHOWING_RESULT')}
                aria-label="Ulangi Pembacaan"
              >
                <svg fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.92-12.28l5.07 5.07"/>
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
      </div>
    </main>
  );
}