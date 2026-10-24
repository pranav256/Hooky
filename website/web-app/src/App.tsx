import { useState, useEffect, useRef } from "react";
import * as THREE from "three";
import { Analytics } from "@vercel/analytics/react";
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
  ChevronDown
} from "lucide-react";
import { Button } from "@/components/ui/button";

// High-impact short-form reel script
const CAPTION_SCRIPT = [
  { words: ["SPECIFIC", "KNOWLEDGE", "CANNOT", "BE", "TAUGHT"], highlight: 1 },
  { words: ["CODE", "AND", "MEDIA", "ARE", "PERMISSIONLESS", "LEVERAGE"], highlight: 4 },
  { words: ["NEVER", "RENT", "OUT", "YOUR", "TIME"], highlight: 0 },
  { words: ["DOPAMINE", "FOLLOWS", "ACTION", "NOT", "THOUGHT"], highlight: 0 },
  { words: ["COMPOUNDING", "CREATES", "UNFAIR", "ADVANTAGES"], highlight: 2 },
];

export function App() {
  const [isPlaying] = useState(true);
  const [phraseIdx, setPhraseIdx] = useState(0);
  const [wordIdx, setWordIdx] = useState(0);
  const [subtitleStyle, setSubtitleStyle] = useState<"hormozi" | "yellow" | "clean">("hormozi");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeCliTab, setActiveCliTab] = useState<"make" | "preview" | "parts" | "doctor">("make");
  const [highlightColor, setHighlightColor] = useState("#FACC15");

  const mountRef = useRef<HTMLDivElement>(null);
  const screenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const screenTextureRef = useRef<THREE.CanvasTexture | null>(null);

  // Animated subtitle cadence
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
    }, 420);
    return () => clearInterval(interval);
  }, [isPlaying, phraseIdx]);

  // 2D Canvas rendering the live 9:16 vertical video onto the 3D phone screen
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

      // 1. Soothing, deep dark cinematic background
      const bgGrad = ctx.createLinearGradient(0, 0, 0, 960);
      bgGrad.addColorStop(0, "#0b0f19");
      bgGrad.addColorStop(0.4, "#131926");
      bgGrad.addColorStop(0.8, "#0c101a");
      bgGrad.addColorStop(1, "#070a12");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, 540, 960);

      // Soft ambient light cone
      const radGrad = ctx.createRadialGradient(270, 360, 30, 270, 360, 260);
      radGrad.addColorStop(0, "rgba(59, 130, 246, 0.16)");
      radGrad.addColorStop(0.6, "rgba(59, 130, 246, 0.04)");
      radGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = radGrad;
      ctx.fillRect(0, 0, 540, 960);

      // 2. Speaker Silhouette in studio framing
      ctx.save();
      // Head
      ctx.beginPath();
      ctx.arc(270, 330, 75, 0, Math.PI * 2);
      ctx.fillStyle = "#1e2638";
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "rgba(148, 163, 184, 0.3)";
      ctx.stroke();

      // Shoulders
      ctx.beginPath();
      ctx.ellipse(270, 470, 135, 75, 0, Math.PI, 0);
      ctx.fillStyle = "#151b27";
      ctx.fill();

      // Podcast Microphone
      ctx.beginPath();
      ctx.roundRect(246, 360, 48, 70, 24);
      ctx.fillStyle = "#283347";
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "#475569";
      ctx.stroke();
      ctx.restore();

      // 3. Smart Active Speaker Face Tracking Box with corner brackets
      const bx = 168, by = 232, bw = 204, bh = 214;
      ctx.save();
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 3;
      const cLen = 20;
      // Top-Left
      ctx.beginPath(); ctx.moveTo(bx, by + cLen); ctx.lineTo(bx, by); ctx.lineTo(bx + cLen, by); ctx.stroke();
      // Top-Right
      ctx.beginPath(); ctx.moveTo(bx + bw - cLen, by); ctx.lineTo(bx + bw, by); ctx.lineTo(bx + bw, by + cLen); ctx.stroke();
      // Bottom-Left
      ctx.beginPath(); ctx.moveTo(bx, by + bh - cLen); ctx.lineTo(bx, by + bh); ctx.lineTo(bx + cLen, by + bh); ctx.stroke();
      // Bottom-Right
      ctx.beginPath(); ctx.moveTo(bx + bw - cLen, by + bh); ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by + bh - cLen); ctx.stroke();

      // Tracking Pill
      ctx.fillStyle = "rgba(2, 132, 199, 0.9)";
      ctx.beginPath();
      ctx.roundRect(bx + 14, by - 13, 126, 22, 5);
      ctx.fill();
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 11px monospace";
      ctx.fillText("● FACE LOCK 99.4%", bx + 22, by + 3);
      ctx.restore();

      // 4. Kinetic Subtitles in Center
      const currentPhrase = CAPTION_SCRIPT[phraseIdx];
      if (currentPhrase) {
        ctx.save();
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.font = `900 36px 'Inter', sans-serif`;

        const words = currentPhrase.words;
        const lineY = 590;
        const fullText = words.join(" ");
        const metrics = ctx.measureText(fullText);
        let curX = 270 - metrics.width / 2;

        words.forEach((w, i) => {
          const wWidth = ctx.measureText(w + " ").width;
          const isCurrent = i === wordIdx;

          if (isCurrent) {
            ctx.shadowColor = highlightColor;
            ctx.shadowBlur = 18;
            ctx.fillStyle = highlightColor;
            ctx.strokeStyle = "#000000";
            ctx.lineWidth = 5;
            ctx.strokeText(w, curX + wWidth / 2, lineY);
            ctx.fillText(w, curX + wWidth / 2, lineY);
            ctx.shadowBlur = 0;
          } else {
            ctx.fillStyle = "#f8fafc";
            ctx.strokeStyle = "#000000";
            ctx.lineWidth = 5;
            ctx.strokeText(w, curX + wWidth / 2, lineY);
            ctx.fillText(w, curX + wWidth / 2, lineY);
          }
          curX += wWidth;
        });
        ctx.restore();
      }

      // 5. Right-side Vertical Action Column
      const actions = [
        { icon: "♥", count: "142K" },
        { icon: "💬", count: "2.4K" },
        { icon: "🔖", count: "28K" },
        { icon: "↗", count: "16K" }
      ];
      ctx.save();
      ctx.textAlign = "center";
      actions.forEach((act, idx) => {
        const ay = 520 + idx * 64;
        ctx.fillStyle = "rgba(15, 23, 42, 0.6)";
        ctx.beginPath();
        ctx.arc(496, ay, 18, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 15px sans-serif";
        ctx.fillText(act.icon, 496, ay + 5);

        ctx.font = "bold 10px sans-serif";
        ctx.fillStyle = "rgba(241, 245, 249, 0.85)";
        ctx.fillText(act.count, 496, ay + 26);
      });
      ctx.restore();

      // 6. Live Audio Equalizer Waveform & Audio Track
      ctx.save();
      const barCount = 26;
      const barWidth = 6;
      for (let i = 0; i < barCount; i++) {
        const height = Math.sin(waveOffset + i * 0.45) * 18 + Math.cos(waveOffset * 1.8 + i * 0.3) * 12 + 20;
        ctx.fillStyle = i % 2 === 0 ? highlightColor : "rgba(248, 250, 252, 0.5)";
        ctx.fillRect(40 + i * 10, 835 - height, barWidth, height);
      }

      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 15px sans-serif";
      ctx.fillText("@hooky_cli • 9:16 Auto-Crop", 40, 875);

      ctx.fillStyle = "rgba(148, 163, 184, 0.9)";
      ctx.font = "12px sans-serif";
      ctx.fillText("♫ Naval on Joe Rogan #1309 • Virality 98.6%", 40, 898);
      ctx.restore();

      // 7. Dynamic Island & Top Status Bar
      ctx.save();
      ctx.fillStyle = "#000000";
      ctx.beginPath();
      ctx.roundRect(210, 20, 120, 28, 14);
      ctx.fill();

      // Camera lens
      ctx.fillStyle = "#1e293b";
      ctx.beginPath();
      ctx.arc(305, 34, 4.5, 0, Math.PI * 2);
      ctx.fill();

      // Status Bar
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 15px sans-serif";
      ctx.fillText("9:41", 44, 40);
      ctx.font = "13px monospace";
      ctx.fillText("5G 100%", 438, 40);
      ctx.restore();

      if (screenTextureRef.current) {
        screenTextureRef.current.needsUpdate = true;
      }
      animId = requestAnimationFrame(renderScreen);
    };

    renderScreen();
    return () => cancelAnimationFrame(animId);
  }, [phraseIdx, wordIdx, highlightColor]);

  // Clean 3D Titanium Smartphone Stage
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
    renderer.toneMappingExposure = 1.0;
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // 3. Soft Studio Lighting (Gentle, low contrast, no blinding flashes)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xe2e8f0, 1.4);
    keyLight.position.set(8, 12, 10);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x94a3b8, 0.6);
    fillLight.position.set(-8, -6, 5);
    scene.add(fillLight);

    // 4. Smartphone Geometry
    const phoneGroup = new THREE.Group();
    scene.add(phoneGroup);

    const createRoundedRect = (w: number, h: number, r: number) => {
      const shape = new THREE.Shape();
      shape.moveTo(-w / 2 + r, -h / 2);
      shape.lineTo(w / 2 - r, -h / 2);
      shape.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
      shape.lineTo(w / 2, h / 2 - r);
      shape.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2);
      shape.lineTo(-w / 2 + r, h / 2);
      shape.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r);
      shape.lineTo(-w / 2, -h / 2 + r);
      shape.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
      return shape;
    };

    // Extruded Chassis (Deep Slate Titanium)
    const phoneGeo = new THREE.ExtrudeGeometry(createRoundedRect(6.3, 12.8, 0.75), {
      depth: 0.44,
      bevelEnabled: true,
      bevelSegments: 5,
      steps: 1,
      bevelSize: 0.08,
      bevelThickness: 0.08,
    });
    const phoneMat = new THREE.MeshStandardMaterial({
      color: 0x141a24,
      metalness: 0.85,
      roughness: 0.25,
    });
    const phoneMesh = new THREE.Mesh(phoneGeo, phoneMat);
    phoneMesh.position.z = -0.22;
    phoneGroup.add(phoneMesh);

    // Screen Plane
    if (screenCanvasRef.current) {
      const screenTex = new THREE.CanvasTexture(screenCanvasRef.current);
      screenTex.minFilter = THREE.LinearFilter;
      screenTextureRef.current = screenTex;

      const screenGeo = new THREE.ShapeGeometry(createRoundedRect(5.84, 12.34, 0.6));
      const screenMat = new THREE.MeshBasicMaterial({ map: screenTex, toneMapped: false });
      const screenMesh = new THREE.Mesh(screenGeo, screenMat);
      screenMesh.position.z = 0.25;
      phoneGroup.add(screenMesh);
    }

    // Hardware Side Buttons
    const btnMat = new THREE.MeshStandardMaterial({ color: 0x222a38, metalness: 0.9, roughness: 0.2 });
    const pwrMesh = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.2, 0.18), btnMat);
    pwrMesh.position.set(3.26, 1.8, 0);
    phoneGroup.add(pwrMesh);

    const volUpMesh = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.9, 0.18), btnMat);
    volUpMesh.position.set(-3.26, 2.2, 0);
    phoneGroup.add(volUpMesh);

    const volDownMesh = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.9, 0.18), btnMat);
    volDownMesh.position.set(-3.26, 1.0, 0);
    phoneGroup.add(volDownMesh);

    // Back Camera Island
    const bumpGeo = new THREE.ExtrudeGeometry(createRoundedRect(2.4, 2.5, 0.4), {
      depth: 0.22,
      bevelEnabled: true,
      bevelSegments: 3,
      bevelSize: 0.05,
      bevelThickness: 0.05,
    });
    const bumpMat = new THREE.MeshStandardMaterial({ color: 0x1b2230, metalness: 0.8, roughness: 0.25 });
    const bumpMesh = new THREE.Mesh(bumpGeo, bumpMat);
    bumpMesh.position.set(-1.6, 4.6, -0.45);
    phoneGroup.add(bumpMesh);

    // 3 Camera Lenses
    for (let r = 0; r < 3; r++) {
      const ringGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.12, 24);
      const ringMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.92, roughness: 0.1 });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      ring.position.set(-1.6 + (r % 2) * 0.85, 4.2 + Math.floor(r / 2) * 0.85, -0.55);
      phoneGroup.add(ring);

      const lensGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.13, 24);
      const lensMat = new THREE.MeshStandardMaterial({ color: 0x05070a, metalness: 0.98, roughness: 0.05 });
      const lens = new THREE.Mesh(lensGeo, lensMat);
      lens.rotation.x = Math.PI / 2;
      lens.position.copy(ring.position);
      phoneGroup.add(lens);
    }

    // 5. Mouse Interaction & Tilt Lerp
    let targetRotX = 0.1;
    let targetRotY = -0.25;
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
        targetRotY += deltaX * 0.006;
        targetRotX += deltaY * 0.006;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      } else {
        const normX = (e.clientX / window.innerWidth) * 2 - 1;
        const normY = -(e.clientY / window.innerHeight) * 2 + 1;
        targetRotY = normX * 0.35;
        targetRotX = -normY * 0.25 + 0.08;
      }
    };

    const handlePointerUp = () => {
      isDragging = false;
    };

    window.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);

    // 6. Animation Loop
    let animationFrame: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrame = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth Lerp Rotation
      phoneGroup.rotation.x += (targetRotX - phoneGroup.rotation.x) * 0.05;
      phoneGroup.rotation.y += (targetRotY - phoneGroup.rotation.y) * 0.05;

      // Responsive Stage Layout (Comfortable positioning on right half on desktop)
      const isDesktop = window.innerWidth >= 1024;
      const targetPosX = isDesktop ? 4.2 : 0;
      const targetPosY = isDesktop ? Math.sin(elapsedTime * 1.2) * 0.25 : -1.0 + Math.sin(elapsedTime * 1.2) * 0.2;
      const targetScale = isDesktop ? 1.05 : 0.72;

      phoneGroup.position.x += (targetPosX - phoneGroup.position.x) * 0.08;
      phoneGroup.position.y = targetPosY;
      phoneGroup.scale.set(targetScale, targetScale, targetScale);

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
    };
  }, []);

  const handleStyleChange = (style: "hormozi" | "yellow" | "clean") => {
    setSubtitleStyle(style);
    const colorMap = {
      hormozi: "#FACC15",
      yellow: "#F59E0B",
      clean: "#38BDF8",
    };
    setHighlightColor(colorMap[style]);
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const cliOutputs = {
    make: (
      <>
        <span className="text-blue-400 font-bold">$ ./hooky.sh make</span>
        <br /><br />
        <span className="text-slate-400">[01/04]</span> Auto-scanning channels.txt for view velocity spikes...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Found winning source: @TheDiaryOfACEO (840k views in 24h) -&gt; <span className="text-emerald-400">QUEUED</span><br />
        <span className="text-slate-400">[02/04]</span> Gemini 2.0 Flash analyzing narrative hook points...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• Segment 1 [01:14 -&gt; 01:52]: <span className="text-blue-300">Score 98.4% (Viral Hook)</span><br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• Segment 2 [12:40 -&gt; 13:22]: <span className="text-emerald-400">Score 94.2%</span><br />
        <span className="text-slate-400">[03/04]</span> Faster-whisper int8 millisecond word-level timing...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Aligned 124 words with frame-accurate ASS karaoke boundaries.<br />
        <span className="text-slate-400">[04/04]</span> GPU NVENC 1080x1920 center-crop transcode at 240 FPS...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-emerald-400">✓ output/diary_of_ceo_clip_01.mp4 generated (38s)</span><br />
        <span className="text-slate-200 font-medium">Done. Added to anti-ban Instagram queue with safe 45m jitter delay.</span>
      </>
    ),
    preview: (
      <>
        <span className="text-blue-400 font-bold">$ ./hooky.sh preview</span>
        <br /><br />
        <span className="text-slate-400">[Dry-Run Mode: Zero disk writes or rendering]</span><br />
        • Parsing pending video: https://www.youtube.com/watch?v=3qHkcs3kG44<br />
        • Title: Naval Ravikant - How to Get Rich Without Getting Lucky<br />
        • Gemini 2.0 Hook Extraction (completed in 1.1s):<br />
        &nbsp;&nbsp;1. [04:12 - 04:48] &quot;Specific knowledge vs competition&quot; (Virality: 98%)<br />
        &nbsp;&nbsp;2. [18:30 - 19:15] &quot;Code and media are permissionless leverage&quot; (Virality: 95%)<br />
        Ready to process. Run <span className="text-blue-300">./hooky.sh</span> to render.
      </>
    ),
    parts: (
      <>
        <span className="text-blue-400 font-bold">$ ./hooky.sh parts masterclass.mp4 --part-duration 60</span>
        <br /><br />
        <span className="text-slate-400">[Episodic Series Engine]</span> Slicing 12-minute interview into 60s segments:<br />
        • Part 1: [00:00 -&gt; 01:00] -&gt; <span className="text-emerald-400">✓ masterclass_part_1.mp4</span><br />
        • Part 2: [01:00 -&gt; 02:00] -&gt; <span className="text-emerald-400">✓ masterclass_part_2.mp4</span><br />
        • Part 3: [02:00 -&gt; 03:00] -&gt; <span className="text-emerald-400">✓ masterclass_part_3.mp4</span><br />
        Burned dynamic sequential &apos;Part N&apos; badges into top header.
      </>
    ),
    doctor: (
      <>
        <span className="text-blue-400 font-bold">$ ./hooky.sh doctor</span>
        <br /><br />
        <span className="text-emerald-400">✓</span> Python Environment: 3.10+ (.venv detected)<br />
        <span className="text-emerald-400">✓</span> FFmpeg Engine: Hardware acceleration active (CUDA / Apple Silicon)<br />
        <span className="text-emerald-400">✓</span> Google Gemini API: Authenticated (gemini-2.0-flash responsive)<br />
        <span className="text-emerald-400">✓</span> faster-whisper: Int8 compute engine loaded<br />
        <span className="text-emerald-400">✓</span> yt-dlp: Validated with cookie session injection<br />
        <span className="text-slate-200 font-medium">All health checks passed. System ready for production workload.</span>
      </>
    ),
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-[#F3F4F6] font-sans selection:bg-[#3B82F6]/30 selection:text-white relative overflow-x-hidden">
      
      {/* Subtle, soft ambient depth (no harsh glaring particles) */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-[#3B82F6]/[0.06] blur-[150px] rounded-full" />
      </div>

      {/* TOP NAVBAR */}
      <header className="fixed top-4 left-0 right-0 z-50 px-4 sm:px-8">
        <div className="max-w-6xl mx-auto h-14 bg-[#131926]/85 backdrop-blur-md border border-white/[0.08] rounded-2xl px-5 flex items-center justify-between shadow-lg">
          <a href="#" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-[#1A2234] border border-white/10 flex items-center justify-center text-[#3B82F6]">
              <Zap className="w-4 h-4 fill-current" />
            </div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-white">Hooky</span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-white/5 text-slate-400 border border-white/10">
                v2.4 • MIT
              </span>
            </div>
          </a>

          <nav className="hidden md:flex items-center gap-7 text-xs font-medium text-slate-400">
            <a href="#pipeline" className="hover:text-white transition-colors">Pipeline</a>
            <a href="#terminal" className="hover:text-white transition-colors">CLI Studio</a>
            <a href="#benchmarks" className="hover:text-white transition-colors">Benchmarks</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
          </nav>

          <div className="flex items-center gap-3">
            <a
              href="https://github.com/pranav256/Hooky"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-slate-300 hover:text-white transition-all"
            >
              <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
              <span>GitHub</span>
            </a>

            <Button
              size="sm"
              className="bg-[#3B82F6] hover:bg-[#2563EB] text-white font-semibold text-xs rounded-xl shadow-sm transition-all"
              onClick={() => {
                document.getElementById("terminal")?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              <span>Install CLI</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </div>
        </div>
      </header>

      {/* HERO SECTION */}
      <section id="hero-3d" className="relative min-h-[90vh] flex items-center justify-center pt-28 pb-12 overflow-hidden">
        {/* Three.js Canvas Container */}
        <div ref={mountRef} className="absolute inset-0 z-10 cursor-grab active:cursor-grabbing" />

        {/* Foreground Content */}
        <div className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 w-full pointer-events-none">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center min-h-[75vh]">
            
            {/* Left Copy */}
            <div className="lg:col-span-6 flex flex-col items-start text-left pointer-events-auto">
              
              <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#131926] border border-white/10 text-slate-300 text-xs font-medium mb-6">
                <Sparkles className="w-3.5 h-3.5 text-[#3B82F6]" />
                <span>Google Gemini 2.0 Flash + Faster-Whisper</span>
              </div>

              <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight leading-[1.08] text-[#F8FAFC] mb-6">
                Turn Long Videos <br />
                Into Viral Shorts. <br />
                <span className="text-[#94A3B8] font-semibold text-3xl sm:text-4xl">100% Free &amp; Open Source.</span>
              </h1>

              <p className="text-[#94A3B8] text-base sm:text-lg max-w-xl leading-relaxed mb-8">
                Autonomous AI detects narrative hooks, tracks active speakers in 9:16, and burns animated Hormozi captions on your local GPU. Zero cloud fees. Zero lock-in.
              </p>

              {/* 1-Click Terminal Pill */}
              <div className="w-full sm:w-auto flex flex-col sm:flex-row items-stretch sm:items-center gap-3 p-1.5 rounded-2xl bg-[#131926] border border-white/10 backdrop-blur-md mb-8 group hover:border-[#3B82F6]/40 transition-all shadow-md">
                <div className="flex items-center gap-2.5 px-3 py-1 font-mono text-xs sm:text-sm text-slate-300">
                  <span className="text-[#3B82F6] font-bold">$</span>
                  <span>git clone https://github.com/pranav256/Hooky.git &amp;&amp; ./hooky.sh</span>
                </div>
                <Button
                  size="sm"
                  className="bg-[#3B82F6] hover:bg-[#2563EB] text-white font-medium text-xs rounded-xl transition-all"
                  onClick={() => handleCopy("git clone https://github.com/pranav256/Hooky.git && ./hooky.sh", "hero-cmd")}
                >
                  {copiedId === "hero-cmd" ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedId === "hero-cmd" ? "Copied" : "Copy"}</span>
                </Button>
              </div>

              {/* Caption Style Switcher */}
              <div className="flex flex-col gap-2 pt-1">
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-[#3B82F6]" />
                  <span>Interactive Subtitle Presets (Renders on 3D Phone):</span>
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  {(["hormozi", "yellow", "clean"] as const).map((style) => (
                    <button
                      key={style}
                      onClick={() => handleStyleChange(style)}
                      className={`px-3 py-1 rounded-lg text-xs font-medium uppercase tracking-wider transition-all border ${
                        subtitleStyle === style
                          ? "bg-[#3B82F6] text-white border-[#3B82F6] shadow-sm"
                          : "bg-[#131926] hover:bg-[#1A2234] text-slate-400 border-white/10"
                      }`}
                    >
                      {style}
                    </button>
                  ))}
                </div>
              </div>

            </div>

            {/* Right Side: Clear space for the 3D Titanium Smartphone */}
            <div className="lg:col-span-6 hidden lg:block pointer-events-none" />

          </div>
        </div>
      </section>

      {/* STATS STRIP */}
      <section className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 mb-24">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 sm:p-8 rounded-2xl bg-[#131926] border border-white/[0.08]">
          <div className="flex flex-col items-center text-center">
            <span className="text-3xl sm:text-4xl font-extrabold text-[#F8FAFC] font-mono">10x</span>
            <span className="text-xs text-slate-400 mt-1 font-medium">Faster than Manual Editing</span>
          </div>
          <div className="flex flex-col items-center text-center">
            <span className="text-3xl sm:text-4xl font-extrabold text-emerald-400 font-mono">$0 / mo</span>
            <span className="text-xs text-slate-400 mt-1 font-medium">100% Free MIT Open Source</span>
          </div>
          <div className="flex flex-col items-center text-center">
            <span className="text-3xl sm:text-4xl font-extrabold text-[#3B82F6] font-mono">240+ FPS</span>
            <span className="text-xs text-slate-400 mt-1 font-medium">CUDA / NVENC Transcode</span>
          </div>
          <div className="flex flex-col items-center text-center">
            <span className="text-3xl sm:text-4xl font-extrabold text-[#F8FAFC] font-mono">0 Cloud</span>
            <span className="text-xs text-slate-400 mt-1 font-medium">Complete Local Data Privacy</span>
          </div>
        </div>
      </section>

      {/* PIPELINE ARCHITECTURE */}
      <section id="pipeline" className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 mb-28 scroll-mt-24">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#131926] border border-white/10 text-slate-300 text-xs font-medium uppercase tracking-wider mb-4">
            <Film className="w-3.5 h-3.5 text-[#3B82F6]" /> High Retention Engine
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#F8FAFC]">
            Autonomous Pipeline Architecture
          </h2>
          <p className="text-sm text-slate-400 mt-2">
            No heavy Docker or databases. Driven cleanly by text files and your local GPU.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          <div className="p-7 rounded-2xl bg-[#131926] border border-white/[0.08] hover:border-[#3B82F6]/30 transition-all flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#1A2234] border border-white/10 flex items-center justify-center text-[#3B82F6] mb-5">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-[#F8FAFC] mb-2.5">Gemini 2.0 Hook Detection</h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-6">
                Analyzes the semantic narrative arc to extract true retention hooks (15s to 60s) calibrated for YouTube Shorts, Reels, and TikTok algorithms.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0F19] border border-white/5 font-mono text-xs text-emerald-400">
              ✓ Hook Virality Score: 98.4%
            </div>
          </div>

          <div className="p-7 rounded-2xl bg-[#131926] border border-white/[0.08] hover:border-[#3B82F6]/30 transition-all flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#1A2234] border border-white/10 flex items-center justify-center text-[#3B82F6] mb-5">
                <Radio className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-[#F8FAFC] mb-2.5">YouTube Channel Auto-Radar</h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-6">
                Drop creator handles in <code className="text-[#3B82F6]">channels.txt</code>. Hooky automatically detects high-velocity viral winners based on rolling view counts and feeds them directly to the render queue.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0F19] border border-white/5 font-mono text-xs text-slate-300">
              @TheDiaryOfACEO | limit=2 style=yellow
            </div>
          </div>

          <div className="p-7 rounded-2xl bg-[#131926] border border-white/[0.08] hover:border-[#3B82F6]/30 transition-all flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-[#1A2234] border border-white/10 flex items-center justify-center text-[#3B82F6] mb-5">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-[#F8FAFC] mb-2.5">Anti-Ban Instagram Poster</h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-6">
                Publishing too fast flags accounts. Hooky implements randomized human cooldown jitter (30m - 2h) and state checkpoint recovery to protect your social accounts completely.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-[#0B0F19] border border-white/5 font-mono text-xs text-emerald-400">
              ✓ Randomized Jitter: ~45m Cooldown
            </div>
          </div>

        </div>
      </section>

      {/* INTERACTIVE CLI TERMINAL ENGINE */}
      <section id="terminal" className="relative z-20 max-w-5xl mx-auto px-4 sm:px-8 mb-28 scroll-mt-24">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#131926] border border-white/10 text-slate-300 text-xs font-medium uppercase tracking-wider mb-4">
            <Cpu className="w-3.5 h-3.5 text-[#3B82F6]" /> Terminal Studio
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-[#F8FAFC]">
            Authentic CLI Command Streams
          </h2>
          <p className="text-sm text-slate-400 mt-2">
            Switch between CLI tasks below to inspect real pipeline executions:
          </p>
        </div>

        <div className="rounded-2xl overflow-hidden bg-[#0D121D] border border-white/10 shadow-xl">
          {/* Terminal Top Bar */}
          <div className="bg-[#141A26] px-6 py-3 border-b border-white/10 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
              <span className="ml-3 font-mono text-xs text-slate-400">bash / powershell</span>
            </div>

            <div className="flex items-center gap-1.5 bg-[#0B0F19] p-1 rounded-xl border border-white/10 text-xs font-mono">
              {(["make", "preview", "parts", "doctor"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveCliTab(tab)}
                  className={`px-3 py-1 rounded-lg transition-all ${
                    activeCliTab === tab
                      ? "bg-[#3B82F6] text-white font-semibold"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  ./hooky.sh {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Terminal Body */}
          <div className="p-6 font-mono text-xs sm:text-sm text-slate-300 min-h-[270px] overflow-x-auto relative leading-relaxed bg-[#0B0F19]">
            <Button
              size="sm"
              variant="outline"
              className="absolute top-4 right-4 bg-[#141A26] hover:bg-[#1E2536] border-white/10 text-xs text-white"
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
          <h2 className="text-3xl font-bold text-[#F8FAFC]">Hardware Benchmarks</h2>
          <p className="text-sm text-slate-400 mt-2">Tested on NVIDIA RTX, Apple Silicon Metal, and Multi-Core CPU:</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono">
          <div className="p-6 rounded-2xl bg-[#131926] border border-white/[0.08]">
            <span className="text-[11px] text-slate-400 block mb-1">NVIDIA NVENC (GPU)</span>
            <span className="text-3xl font-bold text-white block">240+ FPS</span>
            <span className="text-xs text-emerald-400 mt-2 block">1080x1920 60p Transcode</span>
          </div>
          <div className="p-6 rounded-2xl bg-[#131926] border border-white/[0.08]">
            <span className="text-[11px] text-slate-400 block mb-1">FASTER-WHISPER</span>
            <span className="text-3xl font-bold text-white block">int8 / fp16</span>
            <span className="text-xs text-[#3B82F6] mt-2 block">~3.2s per 10m audio</span>
          </div>
          <div className="p-6 rounded-2xl bg-[#131926] border border-white/[0.08]">
            <span className="text-[11px] text-slate-400 block mb-1">RAM OVERHEAD</span>
            <span className="text-3xl font-bold text-white block">&lt; 1.4 GB</span>
            <span className="text-xs text-slate-300 mt-2 block">Auto-memory cleanup</span>
          </div>
          <div className="p-6 rounded-2xl bg-[#131926] border border-white/[0.08]">
            <span className="text-[11px] text-slate-400 block mb-1">PRICING</span>
            <span className="text-3xl font-bold text-emerald-400 block">$0 / mo</span>
            <span className="text-xs text-slate-300 mt-2 block">100% Free MIT License</span>
          </div>
        </div>
      </section>

      {/* FAQ SECTION */}
      <section id="faq" className="relative z-20 max-w-4xl mx-auto px-4 sm:px-8 mb-24 scroll-mt-24">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-[#F8FAFC]">Frequently Asked Questions</h2>
        </div>

        <div className="space-y-3.5 text-sm">
          <details className="p-5 rounded-xl bg-[#131926] border border-white/[0.08] group cursor-pointer">
            <summary className="flex items-center justify-between font-medium text-white list-none">
              <span>Can I run Hooky without a dedicated GPU?</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <p className="mt-3 text-xs text-slate-400 leading-relaxed">
              Yes! Hooky auto-profiles your system on startup. If no NVIDIA CUDA GPU is found, it switches Whisper to int8 CPU mode and leverages multi-threaded CPU FFmpeg encoding.
            </p>
          </details>

          <details className="p-5 rounded-xl bg-[#131926] border border-white/[0.08] group cursor-pointer">
            <summary className="flex items-center justify-between font-medium text-white list-none">
              <span>Does Google Gemini API cost money?</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <p className="mt-3 text-xs text-slate-400 leading-relaxed">
              Google Gemini 2.0 Flash has a generous free tier in Google AI Studio. Since Hooky passes only timestamps and text transcripts (not giant multi-gigabyte video files), token consumption is minimal and fits within free quotas.
            </p>
          </details>

          <details className="p-5 rounded-xl bg-[#131926] border border-white/[0.08] group cursor-pointer">
            <summary className="flex items-center justify-between font-medium text-white list-none">
              <span>How does the automated YouTube channel discovery work?</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <p className="mt-3 text-xs text-slate-400 leading-relaxed">
              Drop YouTube channel handles or URLs into <code className="text-[#3B82F6]">channels.txt</code> (e.g. <code className="text-slate-300">@hubermanlab | limit=3 min_views=250000</code>). When you run <code className="text-[#3B82F6]">./hooky.sh make</code>, Hooky queries the channel's uploads with yt-dlp, calculates view velocity spikes, and queues winning high-retention candidates automatically.
            </p>
          </details>

          <details className="p-5 rounded-xl bg-[#131926] border border-white/[0.08] group cursor-pointer">
            <summary className="flex items-center justify-between font-medium text-white list-none">
              <span>How does the anti-ban Instagram queue keep accounts safe?</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <p className="mt-3 text-xs text-slate-400 leading-relaxed">
              Automated spammers get banned for fixed-interval posts. Hooky randomizes delays between uploads (configurable in <code className="text-[#3B82F6]">.env</code> between 30 mins and 2 hours), restricts uploads to active daylight hours (e.g. 9 AM – 10 PM), and tracks posted video IDs to prevent duplicates.
            </p>
          </details>

          <details className="p-5 rounded-xl bg-[#131926] border border-white/[0.08] group cursor-pointer">
            <summary className="flex items-center justify-between font-medium text-white list-none">
              <span>Can I split long masterclasses or podcasts into Part 1, Part 2, etc.?</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <p className="mt-3 text-xs text-slate-400 leading-relaxed">
              Yes! Run <code className="text-[#3B82F6]">./hooky.sh parts &lt;video.mp4&gt; --part-duration 60</code>. Hooky automatically calculates segment boundaries, burns sequential "Part N" badges into the video header, and outputs clean 60-second vertical reels.
            </p>
          </details>

          <details className="p-5 rounded-xl bg-[#131926] border border-white/[0.08] group cursor-pointer">
            <summary className="flex items-center justify-between font-medium text-white list-none">
              <span>Which subtitle styles and fonts are available?</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <p className="mt-3 text-xs text-slate-400 leading-relaxed">
              Hooky includes three built-in subtitle styles: <code className="text-yellow-400">hormozi</code> (bold uppercase with dynamic spoken word highlights), <code className="text-amber-400">yellow</code> (high-contrast yellow keyword highlights), and <code className="text-sky-300">clean</code> (modern minimalist with subtle background box). Run <code className="text-[#3B82F6]">./hooky.sh styles</code> to preview them.
            </p>
          </details>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="relative z-20 border-t border-white/[0.08] py-10 text-xs font-mono text-slate-400 bg-[#0B0F19]">
        <div className="max-w-6xl mx-auto px-4 sm:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Zap className="w-4 h-4 text-[#3B82F6] fill-current" />
            <span className="text-white font-bold">Hooky</span>
            <span>•</span>
            <span>Autonomous AI Video Clipper (MIT)</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="https://github.com/pranav256/Hooky" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">
              GitHub Repository
            </a>
            <a href="https://github.com/pranav256/Hooky/blob/main/LICENSE" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">
              MIT License
            </a>
          </div>
        </div>
      </footer>

      {/* Vercel Web Analytics */}
      <Analytics />
    </div>
  );
}

export default App;
