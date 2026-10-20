'use client';

import { useState, useEffect, useRef } from 'react';

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
    // Fitur mikrofon dinonaktifkan sementara.
    // Animasi wave akan berjalan selama 3 detik lalu otomatis lanjut ke state berikutnya.
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
        // Simulasi otomatis kembali ke kamera awal setelah selesai "mendengarkan" di akhir
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

  return (
    <main 
      onClick={handleScreenClick}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'black',
        overflow: 'hidden',
        userSelect: 'none'
      }}
    >
      {/* === INJEKSI CSS ANIMASI KEYFRAMES & TOMBOL FLAT === */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes dropInFlex {
          0% { transform: translateY(-100vh); opacity: 0; }
          60% { transform: translateY(20px); opacity: 1; }
          80% { transform: translateY(-10px); opacity: 1; }
          100% { transform: translateY(0); opacity: 1; }
        }
        .animate-drop-flex {
          animation: dropInFlex 0.6s cubic-bezier(0.25, 1, 0.5, 1) forwards;
        }

        @keyframes spinLoader {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-loader {
          animation: spinLoader 1s linear infinite;
        }

        @keyframes soundWave {
          0%, 100% { height: 8px; }
          50% { height: 32px; }
        }
        .animate-wave {
          animation: soundWave 1s ease-in-out infinite;
        }
        .wave-1 { animation-delay: 0.0s; }
        .wave-2 { animation-delay: 0.2s; }
        .wave-3 { animation-delay: 0.4s; }
        .wave-4 { animation-delay: 0.2s; }
        .wave-5 { animation-delay: 0.0s; }

        /* Tombol Flat Semi-Transparan */
        .btn-menu {
          background-color: rgba(249, 115, 22, 0.3);
          color: #1f2937;
          border: none; 
          border-radius: 12px;
          padding: 16px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          text-align: center;
        }
        .btn-menu:hover {
          background-color: var(--jingga, #f97316); 
          color: white; 
        }
        .btn-menu:active {
          transform: scale(0.98); 
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

      {/* === SCREEN 1: PERNAK-PERNIK UI KAMERA === */}
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

      {/* === SCREEN 2 & 4: LOADING === */}
      {(appState === 'PROCESSING_VISION' || appState === 'PROCESSING_Q') && (
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'white', zIndex: 30, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
             <svg 
               className="animate-spin-loader" 
               xmlns="http://www.w3.org/2000/svg" 
               width="80" 
               height="80" 
               viewBox="0 0 24 24" 
               fill="none" 
               stroke="var(--jingga, #f97316)" 
               strokeWidth="2.5" 
               strokeLinecap="round" 
               strokeLinejoin="round"
             >
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
             </svg>
          </div>
      )}

      {/* === SCREEN 3: HASIL FOTO & TEKS === */}
      {(appState === 'PROMPTING_Q' || appState === 'LISTENING_Q') && (
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'white', zIndex: 30, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="animate-drop-flex" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '32px', padding: '24px', width: '100%', maxWidth: '400px' }}>
            
            {capturedImage && (
              <div style={{ width: '100%', display: 'flex', justifyContent: 'center' }}>
                <img 
                  src={capturedImage} 
                  alt="Hasil Foto" 
                  style={{ 
                    maxWidth: '100%', 
                    maxHeight: '55vh', 
                    objectFit: 'contain', 
                    borderRadius: '16px',
                    transform: 'scaleX(-1)', 
                    boxShadow: '0 10px 30px rgba(0,0,0,0.1)' 
                  }} 
                />
              </div>
            )}
            
            <h2 style={{ fontSize: '20px', fontWeight: '800', textAlign: 'center', color: 'black', margin: '0' }}>
              Apa yang ingin anda tanyakan<br/>dari foto ini?
            </h2>

            <div style={{ height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {appState === 'LISTENING_Q' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div className="animate-wave wave-1" style={{ width: '8px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                  <div className="animate-wave wave-2" style={{ width: '8px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                  <div className="animate-wave wave-3" style={{ width: '8px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                  <div className="animate-wave wave-4" style={{ width: '8px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                  <div className="animate-wave wave-5" style={{ width: '8px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                </div>
              )}
            </div>

          </div>
        </div>
      )}

      {/* === SCREEN 5: LAYAR HASIL AKHIR (Foto + Output + Buttons) === */}
      {(appState === 'SHOWING_RESULT' || appState === 'PROMPTING_MENU' || appState === 'LISTENING_MENU') && (
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'white', zIndex: 40, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
          
          <div 
            className="animate-drop-flex"
            style={{ width: '100%', maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '16px' }}
            onClick={(e) => e.stopPropagation()} 
          >
            {capturedImage && (
              <div style={{ width: '100%', display: 'flex', justifyContent: 'center', flexShrink: 0 }}>
                <img 
                  src={capturedImage} 
                  alt="Hasil Foto" 
                  style={{ 
                    maxWidth: '100%', 
                    maxHeight: '35vh', 
                    objectFit: 'contain', 
                    borderRadius: '16px',
                    transform: 'scaleX(-1)', 
                    boxShadow: '0 4px 15px rgba(0,0,0,0.05)'
                  }} 
                />
              </div>
            )}

            {/* INDIKATOR GELOMBANG SUARA */}
            <div style={{ height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {appState === 'LISTENING_MENU' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div className="animate-wave wave-1" style={{ width: '6px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                  <div className="animate-wave wave-2" style={{ width: '6px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                  <div className="animate-wave wave-3" style={{ width: '6px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                  <div className="animate-wave wave-4" style={{ width: '6px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                  <div className="animate-wave wave-5" style={{ width: '6px', backgroundColor: 'var(--jingga, #f97316)', borderRadius: '99px' }}></div>
                </div>
              )}
            </div>

            {/* TEKS OUTPUT */}
            <div style={{ backgroundColor: 'var(--jingga, #f97316)', padding: '16px 20px', borderRadius: '12px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: '700', textAlign: 'center', color: 'white', margin: 0, lineHeight: '1.5' }}>
                {resultText}
              </h2>
            </div>
            
            {/* TOMBOL-TOMBOL MENU FLAT */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '8px' }}>
              <button 
                className="btn-menu"
                onClick={() => setAppState('SHOWING_RESULT')}
              >
                Ulangi Pembacaan
              </button>
              
              <button 
                className="btn-menu"
                onClick={() => setAppState('INIT')}
              >
                Foto Lagi
              </button>
              
              <button 
                className="btn-menu"
                onClick={() => {
                  playSystemAudio("Terima kasih sudah memakai aplikasi kami.");
                  setAppState('IDLE');
                }}
              >
                Keluar
              </button>
            </div>

          </div>
        </div>
      )}
    </main>
  );
}