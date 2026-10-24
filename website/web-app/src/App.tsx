import { useState, useEffect, useRef } from "react";
import * as THREE from "three";
import {
  Copy,
  Check,
  Star,
  ArrowRight,
  Radio,
  ShieldCheck,
  Film,
  Sparkles,
  Zap,
  Sliders,
  Cpu,
  Volume2,
  VolumeX,
  Maximize2,
  ChevronDown
} from "lucide-react";
import { Button } from "@/components/ui/button";

// Sample script for the animated reel
const CAPTION_SCRIPT = [
  { words: ["THE", "BIGGEST", "MISTAKE", "CREATORS", "MAKE"], highlight: 2 },
  { words: ["IS", "WAITING", "FOR", "MOTIVATION", "TO", "STRIKE"], highlight: 3 },
  { words: ["DOPAMINE", "FOLLOWS", "ACTION", "NOT", "THOUGHT"], highlight: 0 },
  { words: ["START", "BEFORE", "YOU", "ARE", "READY"], highlight: 4 },
];

export function App() {
  // Playback & caption state
  const [isPlaying, setIsPlaying] = useState(true);
  const [phraseIdx, setPhraseIdx] = useState(0);
  const [wordIdx, setWordIdx] = useState(0);
  const [subtitleStyle, setSubtitleStyle] = useState<"hormozi" | "yellow" | "clean" | "cyber">("hormozi");
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeCliTab, setActiveCliTab] = useState<"make" | "preview" | "parts" | "doctor">("make");
  const selectedFont = "Montserrat";
  const [highlightColor, setHighlightColor] = useState("#FACC15");

  // Three.js container & canvas refs
  const mountRef = useRef<HTMLDivElement>(null);
  const screenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const screenTextureRef = useRef<THREE.CanvasTexture | null>(null);

  // Audio Context ref
  const audioCtxRef = useRef<AudioContext | null>(null);

  // Synthesizer beep feedback
  const playTone = (freq = 440, duration = 0.08) => {
    if (!soundEnabled) return;
    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === "suspended") ctx.resume();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.06, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch {}
  };

  // Scroll listener for parallax
  useEffect(() => {
    const handleScroll = () => {
      // parallax tracking
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Timer for word-by-word karaoke
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setWordIdx((prev) => {
        const curPhrase = CAPTION_SCRIPT[phraseIdx];
        if (prev + 1 >= curPhrase.words.length) {
          setPhraseIdx((p) => (p + 1) % CAPTION_SCRIPT.length);
          return 0;
        }
        return prev + 1;
      });
    }, 380);
    return () => clearInterval(interval);
  }, [isPlaying, phraseIdx]);

  // Create & continuously update the 2D canvas texture for the 3D phone screen
  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 540;
    canvas.height = 960;
    screenCanvasRef.current = canvas;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let waveOffset = 0;

    const renderScreen = () => {
      waveOffset += 0.08;
      // Background gradient
      const bgGrad = ctx.createLinearGradient(0, 0, 0, 960);
      bgGrad.addColorStop(0, "#0f172a");
      bgGrad.addColorStop(0.5, "#090d16");
      bgGrad.addColorStop(1, "#020408");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, 540, 960);

      // Radial spotlight in center
      const radGrad = ctx.createRadialGradient(270, 480, 20, 270, 480, 280);
      radGrad.addColorStop(0, "rgba(139, 92, 246, 0.25)");
      radGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = radGrad;
      ctx.fillRect(0, 0, 540, 960);

      // Top Notch & Status bar
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 20px monospace";
      ctx.fillText("9:41", 40, 50);
      ctx.fillText("5G 100%", 420, 50);

      // Instagram Reels Header
      ctx.font = "bold 26px sans-serif";
      ctx.fillText("Reels", 40, 110);

      // Speaker Avatar in 3D frame
      ctx.save();
      ctx.beginPath();
      ctx.arc(270, 360, 90, 0, Math.PI * 2);
      ctx.fillStyle = "#1e293b";
      ctx.fill();
      ctx.lineWidth = 4;
      ctx.strokeStyle = "#8b5cf6";
      ctx.stroke();

      // Speaker tracking box
      ctx.strokeStyle = "rgba(16, 185, 129, 0.6)";
      ctx.lineWidth = 2;
      ctx.strokeRect(150, 240, 240, 250);
      ctx.fillStyle = "rgba(16, 185, 129, 0.9)";
      ctx.font = "14px monospace";
      ctx.fillText("AUTO-TRACK: 98.4%", 160, 230);
      ctx.restore();

      // Live animated audio spectrum bars
      const barCount = 28;
      const barWidth = 10;
      const startX = (540 - barCount * 14) / 2;
      for (let i = 0; i < barCount; i++) {
        const height = Math.sin(waveOffset + i * 0.4) * 35 + Math.cos(waveOffset * 1.5 + i * 0.2) * 25 + 40;
        const barGrad = ctx.createLinearGradient(0, 680 - height, 0, 680);
        barGrad.addColorStop(0, highlightColor);
        barGrad.addColorStop(1, "rgba(139, 92, 246, 0.2)");
        ctx.fillStyle = barGrad;
        ctx.fillRect(startX + i * 14, 680 - height, barWidth, height);
      }

      // Hormozi Subtitles in Center
      const currentPhrase = CAPTION_SCRIPT[phraseIdx];
      if (currentPhrase) {
        ctx.save();
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.font = `900 36px ${selectedFont}, sans-serif`;

        // Render current phrase words
        const words = currentPhrase.words;
        const lineY = 560;

        // Word spacing calculation
        const fullText = words.join(" ");
        const metrics = ctx.measureText(fullText);
        let curX = 270 - metrics.width / 2;

        words.forEach((w, i) => {
          const wWidth = ctx.measureText(w + " ").width;
          const isCurrent = i === wordIdx;

          if (isCurrent) {
            ctx.fillStyle = highlightColor;
            ctx.shadowColor = highlightColor;
            ctx.shadowBlur = 18;
            ctx.fillText(w, curX + wWidth / 2, lineY);
            ctx.shadowBlur = 0;
          } else {
            ctx.fillStyle = "#ffffff";
            ctx.fillText(w, curX + wWidth / 2, lineY);
          }
          curX += wWidth;
        });
        ctx.restore();
      }

      // Bottom User bar
      ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
      ctx.font = "bold 20px sans-serif";
      ctx.fillText("@hooky_ai", 40, 880);
      ctx.font = "16px sans-serif";
      ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
      ctx.fillText("Gemini 2.0 Flash • 9:16 Auto-Crop", 40, 910);

      // Tell Three.js texture to update
      if (screenTextureRef.current) {
        screenTextureRef.current.needsUpdate = true;
      }
      animId = requestAnimationFrame(renderScreen);
    };

    renderScreen();
    return () => cancelAnimationFrame(animId);
  }, [phraseIdx, wordIdx, highlightColor, selectedFont]);

  // Full Three.js 3D Smartphone, Orbiting Cards & Starfield
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 18);

    // 2. Renderer
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // 3. Lighting Setup (Dramatic Studio Lighting)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xa78bfa, 2.5);
    keyLight.position.set(10, 15, 15);
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0x06b6d4, 3.0);
    rimLight.position.set(-15, -10, -10);
    scene.add(rimLight);

    const amberLight = new THREE.PointLight(0xf59e0b, 2.0, 50);
    amberLight.position.set(0, -5, 10);
    scene.add(amberLight);

    // 4. Smartphone Construction
    const phoneGroup = new THREE.Group();
    scene.add(phoneGroup);

    // Phone Body Chassis (Dark Titanium Ceramic)
    const phoneGeo = new THREE.BoxGeometry(6.4, 13.0, 0.6);
    const phoneMat = new THREE.MeshStandardMaterial({
      color: 0x0f1118,
      metalness: 0.92,
      roughness: 0.18,
    });
    const phoneMesh = new THREE.Mesh(phoneGeo, phoneMat);
    phoneGroup.add(phoneMesh);

    // Screen Texture Plane
    if (screenCanvasRef.current) {
      const screenTex = new THREE.CanvasTexture(screenCanvasRef.current);
      screenTex.minFilter = THREE.LinearFilter;
      screenTextureRef.current = screenTex;

      const screenGeo = new THREE.PlaneGeometry(5.9, 12.5);
      const screenMat = new THREE.MeshBasicMaterial({
        map: screenTex,
        toneMapped: false,
      });
      const screenMesh = new THREE.Mesh(screenGeo, screenMat);
      screenMesh.position.z = 0.31;
      phoneGroup.add(screenMesh);
    }

    // Camera Bump on Back
    const bumpGeo = new THREE.BoxGeometry(2.4, 2.6, 0.3);
    const bumpMat = new THREE.MeshStandardMaterial({ color: 0x161922, metalness: 0.8, roughness: 0.2 });
    const bumpMesh = new THREE.Mesh(bumpGeo, bumpMat);
    bumpMesh.position.set(-1.6, 4.8, -0.35);
    phoneGroup.add(bumpMesh);

    // Camera Lenses
    for (let r = 0; r < 3; r++) {
      const lensGeo = new THREE.CylinderGeometry(0.4, 0.4, 0.15, 24);
      const lensMat = new THREE.MeshStandardMaterial({ color: 0x05070a, metalness: 0.95, roughness: 0.05 });
      const lens = new THREE.Mesh(lensGeo, lensMat);
      lens.rotation.x = Math.PI / 2;
      lens.position.set(-1.6 + (r % 2) * 0.85, 4.4 + Math.floor(r / 2) * 0.9, -0.5);
      phoneGroup.add(lens);
    }

    // 5. Orbiting 3D Holographic Badges
    const badgeGroup = new THREE.Group();
    scene.add(badgeGroup);

    // Helper to create glowing badge canvas
    const createBadge = (text: string, subtext: string, color: string) => {
      const c = document.createElement("canvas");
      c.width = 320;
      c.height = 120;
      const ctx = c.getContext("2d");
      if (ctx) {
        ctx.fillStyle = "rgba(15, 20, 30, 0.85)";
        ctx.roundRect(4, 4, 312, 112, 20);
        ctx.fill();
        ctx.lineWidth = 3;
        ctx.strokeStyle = color;
        ctx.stroke();

        ctx.fillStyle = color;
        ctx.font = "bold 24px monospace";
        ctx.fillText(text, 24, 48);

        ctx.fillStyle = "#ffffff";
        ctx.font = "18px sans-serif";
        ctx.fillText(subtext, 24, 85);
      }
      const tex = new THREE.CanvasTexture(c);
      const geo = new THREE.PlaneGeometry(3.6, 1.35);
      const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, side: THREE.DoubleSide });
      return new THREE.Mesh(geo, mat);
    };

    const badge1 = createBadge("🔥 98.6% VIRAL HOOK", "Gemini 2.0 Flash Verified", "#f59e0b");
    badge1.position.set(-5.5, 3.5, 2.5);
    badgeGroup.add(badge1);

    const badge2 = createBadge("⚡ 240+ FPS NVENC", "GPU Vertical Transcode", "#06b6d4");
    badge2.position.set(5.5, -2.5, 3.0);
    badgeGroup.add(badge2);

    const badge3 = createBadge("🛡️ ANTI-BAN JITTER", "Instagram Auto-Publisher", "#10b981");
    badge3.position.set(-4.5, -4.5, 1.5);
    badgeGroup.add(badge3);

    // 6. Interactive 3D Particle Constellation (1,200 stars)
    const particleCount = 1200;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const pColors = new Float32Array(particleCount * 3);

    const colorA = new THREE.Color(0xa78bfa); // Violet
    const colorB = new THREE.Color(0x38bdf8); // Cyan
    const colorC = new THREE.Color(0xf59e0b); // Amber

    for (let i = 0; i < particleCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 60;
      positions[i + 1] = (Math.random() - 0.5) * 60;
      positions[i + 2] = (Math.random() - 0.5) * 60;

      const chosenColor = Math.random() > 0.6 ? colorA : Math.random() > 0.3 ? colorB : colorC;
      pColors[i] = chosenColor.r;
      pColors[i + 1] = chosenColor.g;
      pColors[i + 2] = chosenColor.b;
    }
    particleGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute("color", new THREE.BufferAttribute(pColors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.12,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    });
    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // 7. Mouse Interaction & Tilt Lerp
    let targetRotX = 0.15;
    let targetRotY = -0.3;
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;

    const handlePointerDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const handlePointerMove = (e: MouseEvent) => {
      if (isDragging) {
        const deltaX = e.clientX - prevMouseX;
        const deltaY = e.clientY - prevMouseY;
        targetRotY += deltaX * 0.008;
        targetRotX += deltaY * 0.008;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      } else {
        const normX = (e.clientX / window.innerWidth) * 2 - 1;
        const normY = -(e.clientY / window.innerHeight) * 2 + 1;
        targetRotY = normX * 0.45;
        targetRotX = -normY * 0.35 + 0.1;
      }
    };

    const handlePointerUp = () => {
      isDragging = false;
    };

    window.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);

    // 8. Animation Loop
    let animationFrame: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrame = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth Lerp Phone Rotation
      phoneGroup.rotation.x += (targetRotX - phoneGroup.rotation.x) * 0.06;
      phoneGroup.rotation.y += (targetRotY - phoneGroup.rotation.y) * 0.06;

      // Floating gentle oscillation
      phoneGroup.position.y = Math.sin(elapsedTime * 1.5) * 0.35;

      // Orbiting Badges
      badge1.position.y = 3.5 + Math.sin(elapsedTime * 2.0) * 0.25;
      badge2.position.y = -2.5 + Math.cos(elapsedTime * 2.2) * 0.25;
      badge3.position.y = -4.5 + Math.sin(elapsedTime * 1.8) * 0.25;

      // Slow particle field rotation
      particleSystem.rotation.y = elapsedTime * 0.03;
      particleSystem.rotation.x = elapsedTime * 0.015;

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("resize", handleResize);
      renderer.dispose();
      phoneGeo.dispose();
      phoneMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
    };
  }, []);

  // Style change handler
  const handleStyleChange = (style: "hormozi" | "yellow" | "clean" | "cyber") => {
    setSubtitleStyle(style);
    playTone(600, 0.06);
    const colorMap = {
      hormozi: "#FACC15",
      yellow: "#F59E0B",
      clean: "#38BDF8",
      cyber: "#10B981",
    };
    setHighlightColor(colorMap[style]);
  };

  // 1-Click Copy with feedback
  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    playTone(880, 0.08);
    setTimeout(() => setCopiedId(null), 2200);
  };

  // Keyboard shortcut hint
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      if (e.code === "Space") {
        e.preventDefault();
        setIsPlaying((p) => !p);
        playTone(520, 0.05);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const cliOutputs = {
    make: (
      <>
        <span className="text-purple-400 font-bold">$ ./hooky.sh make</span>
        <br /><br />
        <span className="text-cyan-400">[01/04]</span> Auto-scanning channels.txt for view velocity spikes...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Found winning source: @TheDiaryOfACEO (840k views in 24h) -&gt; <span className="text-emerald-400">QUEUED</span><br />
        <span className="text-cyan-400">[02/04]</span> Gemini 2.0 Flash analyzing narrative hook points...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• Segment 1 [01:14 -&gt; 01:52]: <span className="text-amber-400">Score 98.4% (Viral Hook)</span><br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• Segment 2 [12:40 -&gt; 13:22]: <span className="text-emerald-400">Score 94.2%</span><br />
        <span className="text-cyan-400">[03/04]</span> Faster-whisper int8 millisecond word-level timing...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Aligned 124 words with frame-accurate ASS karaoke boundaries.<br />
        <span className="text-cyan-400">[04/04]</span> GPU NVENC 1080x1920 center-crop transcode at 240 FPS...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-emerald-400">✓ output/diary_of_ceo_clip_01.mp4 generated (38s)</span><br />
        <span className="text-white font-bold">Done. Added to anti-ban Instagram queue with safe 45m jitter delay.</span>
      </>
    ),
    preview: (
      <>
        <span className="text-purple-400 font-bold">$ ./hooky.sh preview</span>
        <br /><br />
        <span className="text-slate-400">[Dry-Run Mode: Zero disk writes or rendering]</span><br />
        • Parsing pending video: https://www.youtube.com/watch?v=dQw4w9WgXcQ<br />
        • Gemini 2.0 Hook Extraction (completed in 1.1s):<br />
        &nbsp;&nbsp;1. [02:14 - 02:55] &quot;The $100M mindset pivot&quot; (Virality: 96%)<br />
        &nbsp;&nbsp;2. [14:10 - 14:48] &quot;Why 99% fail early&quot; (Virality: 93%)<br />
        Ready to process. Run <span className="text-purple-300">./hooky.sh</span> to render.
      </>
    ),
    parts: (
      <>
        <span className="text-purple-400 font-bold">$ ./hooky.sh parts masterclass.mp4 --part-duration 60</span>
        <br /><br />
        <span className="text-cyan-400">[Episodic Series Engine]</span> Slicing 12-minute interview into 60s segments:<br />
        • Part 1: [00:00 -&gt; 01:00] -&gt; <span className="text-emerald-400">✓ masterclass_part_1.mp4</span><br />
        • Part 2: [01:00 -&gt; 02:00] -&gt; <span className="text-emerald-400">✓ masterclass_part_2.mp4</span><br />
        • Part 3: [02:00 -&gt; 03:00] -&gt; <span className="text-emerald-400">✓ masterclass_part_3.mp4</span><br />
        Burned dynamic sequential &apos;Part N&apos; badges into top header.
      </>
    ),
    doctor: (
      <>
        <span className="text-purple-400 font-bold">$ ./hooky.sh doctor</span>
        <br /><br />
        <span className="text-emerald-400">✓</span> Python Environment: 3.13.x (.venv detected)<br />
        <span className="text-emerald-400">✓</span> FFmpeg Engine: v7.0.1 (NVIDIA CUDA &amp; NVENC hardware acceleration active)<br />
        <span className="text-emerald-400">✓</span> Google Gemini API: Authenticated (gemini-2.0-flash responsive)<br />
        <span className="text-emerald-400">✓</span> faster-whisper: Int8 compute engine loaded on GPU<br />
        <span className="text-emerald-400">✓</span> yt-dlp: Validated with browser cookie session injection<br />
        <span className="text-white font-bold">All health checks passed. System ready for production workload.</span>
      </>
    ),
  };

  return (
    <div className="min-h-screen bg-[#030407] text-[#EDEDED] font-sans selection:bg-purple-600 selection:text-white relative overflow-x-hidden">
      
      {/* 3D WebGL Background & Interactive Phone Hero */}
      <div className="fixed inset-0 pointer-events-none z-0">
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 bg-[radial-gradient(#ffffff0a_1px,transparent_1px)] [background-size:32px_32px] opacity-40" />
      </div>

      {/* TOP FLOATING NAVBAR */}
      <header className="fixed top-4 left-0 right-0 z-50 px-4 sm:px-8">
        <div className="max-w-6xl mx-auto h-14 bg-[#0a0d14]/80 backdrop-blur-xl border border-white/10 rounded-2xl px-5 flex items-center justify-between shadow-2xl">
          <a href="#" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-500 to-cyan-400 p-[1.5px] transition-transform duration-300 group-hover:scale-105">
              <div className="w-full h-full bg-[#090b12] rounded-[10px] flex items-center justify-center">
                <Zap className="w-4 h-4 text-purple-400 fill-purple-400" />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-base tracking-tight text-white">Hooky</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-900/40 text-purple-300 border border-purple-500/30">
                v2.1 MIT
              </span>
            </div>
          </a>

          <nav className="hidden md:flex items-center gap-7 text-xs font-medium text-slate-300">
            <a href="#hero-3d" className="hover:text-purple-400 transition-colors flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" /> 3D Stage
            </a>
            <a href="#pipeline" className="hover:text-white transition-colors">Pipeline</a>
            <a href="#terminal" className="hover:text-white transition-colors">CLI Studio</a>
            <a href="#benchmarks" className="hover:text-white transition-colors">Hardware Benchmarks</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
          </nav>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setSoundEnabled(!soundEnabled);
                playTone(soundEnabled ? 300 : 880, 0.1);
              }}
              title="Toggle Synthesizer Feedback Sound"
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white transition-all"
            >
              {soundEnabled ? <Volume2 className="w-4 h-4 text-purple-400" /> : <VolumeX className="w-4 h-4 text-slate-500" />}
            </button>

            <a
              href="https://github.com/pranav256/Hooky"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-200 transition-all hover:scale-105"
            >
              <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
              <span>Star on GitHub</span>
            </a>

            <Button
              size="sm"
              className="bg-gradient-to-r from-purple-600 to-cyan-500 hover:from-purple-500 hover:to-cyan-400 text-white font-bold text-xs rounded-xl shadow-lg shadow-purple-600/30"
              onClick={() => {
                document.getElementById("terminal")?.scrollIntoView({ behavior: "smooth" });
                playTone(700, 0.08);
              }}
            >
              <span>Install CLI</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </div>
        </div>
      </header>

      {/* HERO SECTION WITH INTERACTIVE 3D WEBGL PHONE */}
      <section id="hero-3d" className="relative min-h-[92vh] flex items-center justify-center pt-24 pb-12 overflow-hidden">
        {/* Three.js Canvas Container (Interactive 3D Stage) */}
        <div ref={mountRef} className="absolute inset-0 z-10 cursor-grab active:cursor-grabbing" />

        {/* Foreground Content (Overlaying 3D with Parallax) */}
        <div className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 w-full pointer-events-none">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center min-h-[75vh]">
            
            {/* Left Copy */}
            <div className="lg:col-span-6 flex flex-col items-start text-left pointer-events-auto">
              
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-purple-950/60 border border-purple-500/30 text-purple-300 text-xs font-semibold mb-6 shadow-lg shadow-purple-950/40">
                <Sparkles className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                <span>Google Gemini 2.0 Flash + Faster-Whisper</span>
              </div>

              <h1 className="text-4xl sm:text-6xl font-black tracking-tight leading-[1.05] text-white mb-6">
                Turn 1-Hour Videos <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400">
                  Into 10 Viral Reels.
                </span><br />
                <span className="text-slate-400">Fully Autonomous.</span>
              </h1>

              <p className="text-slate-300 text-base sm:text-lg max-w-xl leading-relaxed mb-8 font-normal">
                The open-source Opus Clip &amp; Klap alternative. Auto-detects narrative hooks, burns frame-accurate Hormozi kinetic captions, and publishes rate-limited Instagram Reels on your local GPU.
              </p>

              {/* 1-Click Terminal Pill */}
              <div className="w-full sm:w-auto flex flex-col sm:flex-row items-stretch sm:items-center gap-3 p-1.5 rounded-2xl bg-black/70 border border-purple-500/30 backdrop-blur-xl mb-8 group hover:border-purple-500/60 transition-all shadow-2xl">
                <div className="flex items-center gap-2.5 px-3 py-1 font-mono text-xs sm:text-sm text-purple-200">
                  <span className="text-purple-400 font-bold">$</span>
                  <span>git clone https://github.com/pranav256/Hooky.git &amp;&amp; ./hooky.sh</span>
                </div>
                <Button
                  size="sm"
                  className="bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl transition-all shadow-md shadow-purple-600/40"
                  onClick={() => handleCopy("git clone https://github.com/pranav256/Hooky.git && ./hooky.sh", "hero-cmd")}
                >
                  {copiedId === "hero-cmd" ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedId === "hero-cmd" ? "Copied" : "Copy"}</span>
                </Button>
              </div>

              {/* Live Interactive Subtitle Presets Switcher */}
              <div className="flex flex-col gap-2 pt-2">
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-purple-400" />
                  <span>Select Caption Style (Renders on 3D Phone):</span>
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  {(["hormozi", "yellow", "clean", "cyber"] as const).map((style) => (
                    <button
                      key={style}
                      onClick={() => handleStyleChange(style)}
                      className={`px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all border ${
                        subtitleStyle === style
                          ? "bg-purple-600 text-white border-purple-400 shadow-lg shadow-purple-600/40 scale-105"
                          : "bg-white/5 hover:bg-white/10 text-slate-300 border-white/10"
                      }`}
                    >
                      {style}
                    </button>
                  ))}
                </div>
              </div>

            </div>

            {/* Right Side: Interactive 3D Orbiting Hint */}
            <div className="lg:col-span-6 flex flex-col items-center justify-end pointer-events-auto h-full pb-8">
              <div className="p-3 rounded-2xl bg-black/60 backdrop-blur-md border border-white/10 text-center flex items-center gap-3 text-xs font-mono text-purple-200">
                <span className="flex h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
                <span>Drag with mouse to rotate 3D phone 360°</span>
                <Maximize2 className="w-3.5 h-3.5 text-slate-400" />
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* PARALLAX STATS STRIP */}
      <section className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 mb-24">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 sm:p-8 rounded-3xl bg-[#090c14]/90 backdrop-blur-xl border border-white/10 shadow-2xl">
          <div className="flex flex-col items-center text-center">
            <span className="text-3xl sm:text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-300 font-mono">10x</span>
            <span className="text-xs text-slate-400 mt-1 font-medium">Faster than Manual Editing</span>
          </div>
          <div className="flex flex-col items-center text-center">
            <span className="text-3xl sm:text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-300 font-mono">$0 / mo</span>
            <span className="text-xs text-slate-400 mt-1 font-medium">100% Free MIT Open Source</span>
          </div>
          <div className="flex flex-col items-center text-center">
            <span className="text-3xl sm:text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-orange-300 font-mono">240+ FPS</span>
            <span className="text-xs text-slate-400 mt-1 font-medium">CUDA / NVENC GPU Transcode</span>
          </div>
          <div className="flex flex-col items-center text-center">
            <span className="text-3xl sm:text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-300 font-mono">0 Cloud</span>
            <span className="text-xs text-slate-400 mt-1 font-medium">Complete Local Data Privacy</span>
          </div>
        </div>
      </section>

      {/* MODULAR PIPELINE ARCHITECTURE (Animated Cards) */}
      <section id="pipeline" className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 mb-28 scroll-mt-24">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/50 border border-cyan-500/30 text-cyan-300 text-xs font-semibold uppercase tracking-wider mb-4">
            <Film className="w-3.5 h-3.5" /> High Retention Engine
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white">
            How Hooky Turns Podcasts Into <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-cyan-400">
              Viral Vertical Masterpieces
            </span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          <div className="p-8 rounded-3xl bg-[#090c14]/80 backdrop-blur-xl border border-white/10 hover:border-purple-500/50 transition-all hover:-translate-y-1 shadow-xl group">
            <div className="w-12 h-12 rounded-2xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400 mb-6 group-hover:scale-110 transition-transform">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-white mb-3">Gemini 2.0 Hook Detection</h3>
            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Unlike clunky clippers that slice random audio spikes, Hooky analyzes the semantic narrative arc to extract true retention hooks (15s to 60s) calibrated for YouTube and Instagram algorithms.
            </p>
            <div className="p-3 rounded-xl bg-black/60 border border-white/10 font-mono text-xs text-emerald-400">
              ✓ Hook Retention Score: 98.4%
            </div>
          </div>

          <div className="p-8 rounded-3xl bg-[#090c14]/80 backdrop-blur-xl border border-white/10 hover:border-cyan-500/50 transition-all hover:-translate-y-1 shadow-xl group">
            <div className="w-12 h-12 rounded-2xl bg-cyan-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-6 group-hover:scale-110 transition-transform">
              <Radio className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-white mb-3">YouTube Channel Auto-Radar</h3>
            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Drop creator handles in <code className="text-purple-300">channels.txt</code>. Hooky automatically detects high-velocity viral winners based on rolling view counts and feeds them directly to the render queue.
            </p>
            <div className="p-3 rounded-xl bg-black/60 border border-white/10 font-mono text-xs text-cyan-300">
              @TheDiaryOfACEO | limit=2 style=yellow
            </div>
          </div>

          <div className="p-8 rounded-3xl bg-[#090c14]/80 backdrop-blur-xl border border-white/10 hover:border-emerald-500/50 transition-all hover:-translate-y-1 shadow-xl group">
            <div className="w-12 h-12 rounded-2xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-6 group-hover:scale-110 transition-transform">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-white mb-3">Anti-Ban Instagram Poster</h3>
            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Publishing too fast flags accounts. Hooky implements randomized human cooldown jitter (30m - 2h) and state checkpoint recovery to protect your social accounts completely.
            </p>
            <div className="p-3 rounded-xl bg-black/60 border border-white/10 font-mono text-xs text-emerald-300">
              ✓ Randomized Jitter: ~45m Cooldown
            </div>
          </div>

        </div>
      </section>

      {/* INTERACTIVE CLI TERMINAL ENGINE */}
      <section id="terminal" className="relative z-20 max-w-5xl mx-auto px-4 sm:px-8 mb-28 scroll-mt-24">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/50 border border-purple-500/30 text-purple-300 text-xs font-semibold uppercase tracking-wider mb-4">
            <Cpu className="w-3.5 h-3.5" /> Terminal Powerhouse
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white">
            Built For Developers &amp; Power Creators
          </h2>
          <p className="text-sm text-slate-400 mt-2">
            Switch between CLI tasks below to see authentic execution streams:
          </p>
        </div>

        <div className="rounded-3xl overflow-hidden bg-[#07090f] border border-white/15 shadow-2xl">
          {/* Terminal Top Bar */}
          <div className="bg-[#0e121e] px-6 py-3.5 border-b border-white/10 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-500" />
              <span className="w-3 h-3 rounded-full bg-amber-500" />
              <span className="w-3 h-3 rounded-full bg-emerald-500" />
              <span className="ml-3 font-mono text-xs text-slate-400">bash / powershell</span>
            </div>

            <div className="flex items-center gap-1.5 bg-black/50 p-1 rounded-xl border border-white/10 text-xs font-mono">
              {(["make", "preview", "parts", "doctor"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setActiveCliTab(tab);
                    playTone(550, 0.05);
                  }}
                  className={`px-3 py-1 rounded-lg transition-all ${
                    activeCliTab === tab
                      ? "bg-purple-600 text-white font-bold shadow-md shadow-purple-600/40"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  ./hooky.sh {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Terminal Body */}
          <div className="p-6 font-mono text-xs sm:text-sm text-slate-200 min-h-[280px] overflow-x-auto relative leading-relaxed bg-[#05060b]">
            <Button
              size="sm"
              variant="outline"
              className="absolute top-4 right-4 bg-white/10 hover:bg-white/20 border-white/15 text-xs text-white"
              onClick={() => handleCopy(`./hooky.sh ${activeCliTab}`, "cli-copy")}
            >
              {copiedId === "cli-copy" ? <Check className="w-3.5 h-3.5 text-emerald-400 mr-1" /> : <Copy className="w-3.5 h-3.5 mr-1" />}
              <span>{copiedId === "cli-copy" ? "Copied" : "Copy Command"}</span>
            </Button>
            <div className="font-mono">{cliOutputs[activeCliTab]}</div>
          </div>
        </div>
      </section>

      {/* HARDWARE BENCHMARKS */}
      <section id="benchmarks" className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 mb-28 scroll-mt-24">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl font-extrabold text-white">Hardware Profiling &amp; Latency</h2>
          <p className="text-sm text-slate-400 mt-2">Benchmarks measured across NVIDIA RTX, Apple Silicon, and Multi-Core CPU:</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono">
          <div className="p-6 rounded-2xl bg-[#090c14]/90 border border-white/10">
            <span className="text-[10px] text-slate-400 block mb-1">NVIDIA NVENC (GPU)</span>
            <span className="text-3xl font-bold text-white block">240+ FPS</span>
            <span className="text-xs text-emerald-400 mt-2 block">1080x1920 60p Transcode</span>
          </div>
          <div className="p-6 rounded-2xl bg-[#090c14]/90 border border-white/10">
            <span className="text-[10px] text-slate-400 block mb-1">FASTER-WHISPER</span>
            <span className="text-3xl font-bold text-white block">int8 / fp16</span>
            <span className="text-xs text-cyan-300 mt-2 block">~3.2s per 10m audio</span>
          </div>
          <div className="p-6 rounded-2xl bg-[#090c14]/90 border border-white/10">
            <span className="text-[10px] text-slate-400 block mb-1">RAM OVERHEAD</span>
            <span className="text-3xl font-bold text-white block">&lt; 1.4 GB</span>
            <span className="text-xs text-slate-300 mt-2 block">Auto-memory cleanup</span>
          </div>
          <div className="p-6 rounded-2xl bg-[#090c14]/90 border border-white/10">
            <span className="text-[10px] text-slate-400 block mb-1">PRICING</span>
            <span className="text-3xl font-bold text-emerald-400 block">$0 / mo</span>
            <span className="text-xs text-slate-300 mt-2 block">100% Free MIT License</span>
          </div>
        </div>
      </section>

      {/* FAQ SECTION */}
      <section id="faq" className="relative z-20 max-w-4xl mx-auto px-4 sm:px-8 mb-24 scroll-mt-24">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-extrabold text-white">Frequently Asked Questions</h2>
        </div>

        <div className="space-y-4 text-sm">
          <details className="p-5 rounded-2xl bg-[#090c14] border border-white/10 group cursor-pointer">
            <summary className="flex items-center justify-between font-bold text-white list-none">
              <span>Can I run Hooky without a dedicated GPU?</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <p className="mt-3 text-xs text-slate-300 leading-relaxed">
              Yes! Hooky auto-profiles your system on startup. If no NVIDIA CUDA GPU is found, it switches Whisper to int8 CPU mode and leverages multi-threaded CPU FFmpeg encoding.
            </p>
          </details>

          <details className="p-5 rounded-2xl bg-[#090c14] border border-white/10 group cursor-pointer">
            <summary className="flex items-center justify-between font-bold text-white list-none">
              <span>Does Google Gemini API cost money?</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <p className="mt-3 text-xs text-slate-300 leading-relaxed">
              Google Gemini 2.0 Flash has a generous free tier in Google AI Studio. Since Hooky passes only timestamps and text transcripts (not giant multi-gigabyte video files), token consumption is minimal and fits within free quotas.
            </p>
          </details>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="relative z-20 border-t border-white/10 py-10 text-xs font-mono text-slate-500 bg-[#020306]">
        <div className="max-w-6xl mx-auto px-4 sm:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Zap className="w-4 h-4 text-purple-400 fill-purple-400" />
            <span className="text-white font-bold">Hooky</span>
            <span>•</span>
            <span>Autonomous AI Video Clipper (MIT)</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="https://github.com/pranav256/Hooky" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">
              GitHub Repository
            </a>
            <a href="https://github.com/pranav256/Hooky/blob/main/LICENSE" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">
              License
            </a>
          </div>
        </div>
      </footer>

    </div>
  );
}

export default App;
