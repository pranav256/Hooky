"use client";

import { useState, useEffect } from "react";
import { Copy, Check, Sparkles, Sliders, Play, Pause, Crop, Maximize2, Volume2, VolumeX, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

const SCRIPT_WORDS = [
  ["SPECIFIC", "KNOWLEDGE", "CANNOT", "BE", "TAUGHT"],
  ["CODE", "AND", "MEDIA", "ARE", "PERMISSIONLESS", "LEVERAGE"],
  ["NEVER", "RENT", "OUT", "YOUR", "TIME"],
  ["DOPAMINE", "FOLLOWS", "ACTION", "NOT", "THOUGHT"],
  ["COMPOUNDING", "CREATES", "UNFAIR", "ADVANTAGES"],
];

type SubtitlePreset = "hormozi" | "gold" | "clean" | "minimal" | "emerald" | "crimson";
type FramingMode = "center" | "fit";

export function Hero() {
  const [copied, setCopied] = useState(false);
  const [subtitleStyle, setSubtitleStyle] = useState<SubtitlePreset>("hormozi");
  const [framingMode, setFramingMode] = useState<FramingMode>("center");
  const [phraseIdx, setPhraseIdx] = useState(0);
  const [wordIdx, setWordIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(true);

  // Word-by-word kinetic caption cadence
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setWordIdx((prev) => {
        const curPhrase = SCRIPT_WORDS[phraseIdx];
        if (prev + 1 >= curPhrase.length) {
          setPhraseIdx((p) => (p + 1) % SCRIPT_WORDS.length);
          return 0;
        }
        return prev + 1;
      });
    }, 420);
    return () => clearInterval(interval);
  }, [isPlaying, phraseIdx]);

  const handleCopy = () => {
    navigator.clipboard.writeText("git clone https://github.com/pranav256/Hooky.git && ./hooky.sh");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const currentWords = SCRIPT_WORDS[phraseIdx];

  const subtitleStylesMeta: Record<SubtitlePreset, { label: string; desc: string }> = {
    hormozi: { label: "Hormozi Classic", desc: "Bold punchy uppercase with animated yellow word pop" },
    gold: { label: "Warm Titanium", desc: "Refined champagne gold accent with soft glow" },
    clean: { label: "Clean Studio", desc: "Modern sans-serif with frosted dark backdrop pill" },
    minimal: { label: "Minimal Editorial", desc: "Crisp white typography with warm underline" },
    emerald: { label: "Cyber Emerald", desc: "Vibrant neon-green monospace highlight" },
    crimson: { label: "Crimson Impact", desc: "Deep ruby keyword emphasis for dramatic moments" },
  };

  return (
    <section id="demo" className="relative pt-32 pb-20 px-4 sm:px-8 overflow-hidden">
      {/* Soft warm ambient gradient (gentle on eyes) */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[360px] bg-[#E5C07B]/[0.03] blur-[160px] pointer-events-none rounded-full" />

      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          
          {/* Left Column: Value Proposition & Interactive Controls */}
          <div className="lg:col-span-6 flex flex-col items-start text-left">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#10141E] border border-[#E5C07B]/20 text-[#E5C07B] text-xs font-medium mb-6 shadow-sm">
              <Sparkles className="w-3.5 h-3.5 text-[#E5C07B]" />
              <span>Gemini 2.0 Flash • Faster-Whisper • Local GPU FFmpeg</span>
            </div>

            <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight leading-[1.08] text-[#F8FAFC] mb-6">
              Turn Long Videos <br />
              Into Vertical Shorts. <br />
              <span className="text-[#E5C07B] font-semibold text-3xl sm:text-4xl">100% Free &amp; Open Source.</span>
            </h1>

            <p className="text-[#94A3B8] text-base sm:text-lg max-w-xl leading-relaxed mb-8">
              Autonomous AI detects semantic narrative hooks, applies intelligent 9:16 framing (solo center-crop or dual-speaker blur fit), and burns word-level animated captions on your local GPU.
            </p>

            {/* 1-Click Terminal Pill */}
            <div className="w-full sm:w-auto flex flex-col sm:flex-row items-stretch sm:items-center gap-3 p-1.5 rounded-2xl bg-[#10141E] border border-white/10 backdrop-blur-md mb-8 group hover:border-[#E5C07B]/40 transition-all shadow-md">
              <div className="flex items-center gap-2.5 px-3 py-1 font-mono text-xs sm:text-sm text-slate-300">
                <span className="text-[#E5C07B] font-bold">$</span>
                <span className="truncate">git clone https://github.com/pranav256/Hooky.git &amp;&amp; ./hooky.sh</span>
              </div>
              <Button
                size="sm"
                variant="gold"
                className="shrink-0"
                onClick={handleCopy}
              >
                {copied ? <Check className="w-3.5 h-3.5 text-black mr-1" /> : <Copy className="w-3.5 h-3.5 text-black mr-1" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </Button>
            </div>

            {/* Framing & Subtitle Controls */}
            <div className="w-full space-y-4 pt-1">
              {/* Framing Mode Selector */}
              <div>
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                  <Crop className="w-3.5 h-3.5 text-[#E5C07B]" />
                  <span>Smart Video Framing Mode:</span>
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setFramingMode("center")}
                    className={`px-3 py-2 rounded-xl text-xs font-medium text-left transition-all border ${
                      framingMode === "center"
                        ? "bg-[#171D2B] text-white border-[#E5C07B]/60 shadow-sm"
                        : "bg-[#10141E] hover:bg-[#151A26] text-slate-400 border-white/5"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="font-semibold text-white">Center Crop</span>
                      <span className="text-[10px] font-mono text-[#E5C07B]">1080x1920</span>
                    </div>
                    <p className="text-[11px] text-slate-400">Direct portrait close-up focused on active speaker</p>
                  </button>

                  <button
                    onClick={() => setFramingMode("fit")}
                    className={`px-3 py-2 rounded-xl text-xs font-medium text-left transition-all border ${
                      framingMode === "fit"
                        ? "bg-[#171D2B] text-white border-[#E5C07B]/60 shadow-sm"
                        : "bg-[#10141E] hover:bg-[#151A26] text-slate-400 border-white/5"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="font-semibold text-white">Canvas Fit</span>
                      <span className="text-[10px] font-mono text-emerald-400">Ambient Blur</span>
                    </div>
                    <p className="text-[11px] text-slate-400">Preserves multi-speaker wide shots with blur padding</p>
                  </button>
                </div>
              </div>

              {/* Subtitle Style Preset Switcher */}
              <div>
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                  <Sliders className="w-3.5 h-3.5 text-[#E5C07B]" />
                  <span>Interactive Subtitle Presets (6 Styles):</span>
                </span>
                <div className="grid grid-cols-3 sm:grid-cols-3 gap-1.5">
                  {(Object.keys(subtitleStylesMeta) as SubtitlePreset[]).map((style) => (
                    <button
                      key={style}
                      onClick={() => setSubtitleStyle(style)}
                      className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all text-center border truncate ${
                        subtitleStyle === style
                          ? "bg-[#E5C07B] text-[#0A0D14] font-semibold border-[#E5C07B] shadow-sm"
                          : "bg-[#10141E] hover:bg-[#151A26] text-slate-300 border-white/5"
                      }`}
                      title={subtitleStylesMeta[style].desc}
                    >
                      {subtitleStylesMeta[style].label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

          </div>

          {/* Right Column: Live Interactive Visual Studio */}
          <div className="lg:col-span-6 w-full">
            <div className="rounded-2xl bg-[#10141E] border border-white/[0.08] shadow-2xl p-5 relative overflow-hidden">
              
              {/* Studio Header Bar */}
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-white/[0.06] text-xs">
                <div className="flex items-center gap-2 text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-semibold text-white">Hooky Visual Canvas</span>
                  <span className="text-slate-600">•</span>
                  <span className="text-slate-400 font-mono text-[11px]">
                    {framingMode === "center" ? "Portrait Close-Up" : "Wide Multi-Speaker Ambient"}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsMuted(!isMuted)}
                    className="p-1 rounded-lg bg-[#080A0F] border border-white/10 text-slate-400 hover:text-white transition-colors"
                  >
                    {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#080A0F] border border-white/10 text-slate-300 hover:text-white font-mono text-[11px] transition-colors"
                  >
                    {isPlaying ? <Pause className="w-3 h-3 text-[#E5C07B]" /> : <Play className="w-3 h-3 text-emerald-400" />}
                    <span>{isPlaying ? "Live" : "Paused"}</span>
                  </button>
                </div>
              </div>

              {/* 16:9 Master with Framing Representation */}
              <div className="aspect-[16/9] w-full rounded-xl bg-[#080A0F] border border-white/10 relative overflow-hidden flex items-center justify-center">
                {/* Background base */}
                <div className="absolute inset-0 bg-gradient-to-r from-[#0C101A] via-[#141A28] to-[#0C101A] opacity-90" />

                {/* Left Speaker / Host */}
                <div className={`absolute left-[16%] top-[26%] flex flex-col items-center transition-all duration-300 ${
                  framingMode === "center" ? "opacity-35" : "opacity-90"
                }`}>
                  <div className="w-16 h-16 rounded-full bg-slate-800/90 mb-2 border border-white/10" />
                  <div className="w-28 h-14 rounded-t-full bg-slate-800/80" />
                  <span className="text-[10px] font-mono text-slate-400 mt-1">Host</span>
                </div>

                {/* Right Speaker (Active Speaker) */}
                <div className="absolute right-[28%] top-[24%] flex flex-col items-center">
                  <div className="w-18 h-18 rounded-full bg-[#1A2234] border border-[#E5C07B]/50 shadow-lg shadow-[#E5C07B]/10 mb-2 relative">
                    <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 border-2 border-[#10141E]" />
                  </div>
                  <div className="w-32 h-16 rounded-t-full bg-[#1A2234] border-t border-[#E5C07B]/30" />
                  <span className="text-[10px] font-mono text-[#E5C07B] mt-1 font-semibold">Active Speaker</span>
                </div>

                {/* Framing Mode: Mode 1 = Center Crop box */}
                {framingMode === "center" ? (
                  <div className="absolute inset-y-2 right-[20%] w-[33%] rounded-lg border-2 border-[#E5C07B] bg-[#E5C07B]/[0.05] backdrop-blur-[0.5px] shadow-2xl flex flex-col justify-between p-2.5 transition-all duration-300">
                    <div className="flex items-center justify-between text-[9px] font-mono">
                      <span className="bg-[#E5C07B] text-[#0A0D14] px-1.5 py-0.5 rounded font-bold shadow-sm">
                        9:16 CROP
                      </span>
                      <span className="text-emerald-400 bg-black/60 px-1 py-0.5 rounded">
                        SPEAKER FOCUS
                      </span>
                    </div>

                    {/* Word-by-Word Kinetic Subtitle */}
                    <div className="text-center my-auto px-1">
                      <div className={`inline-block px-2.5 py-1.5 rounded-lg max-w-full transition-all ${
                        subtitleStyle === "clean" ? "bg-black/90 border border-white/20" :
                        subtitleStyle === "gold" ? "bg-black/85 border border-[#E5C07B]/30" :
                        subtitleStyle === "emerald" ? "bg-black/90 border border-emerald-500/30 font-mono" :
                        subtitleStyle === "crimson" ? "bg-black/90 border border-rose-500/30" :
                        subtitleStyle === "minimal" ? "bg-transparent" :
                        "bg-black/80 backdrop-blur-md border border-white/10"
                      }`}>
                        <div className="flex flex-wrap justify-center gap-1 text-xs font-black tracking-wide">
                          {currentWords.map((word, wIdx) => {
                            const isActive = wIdx === wordIdx;
                            return (
                              <span
                                key={wIdx}
                                className={`transition-all duration-150 ${
                                  isActive
                                    ? subtitleStyle === "hormozi"
                                      ? "text-yellow-400 scale-110 drop-shadow-[0_2px_8px_rgba(250,204,21,0.6)]"
                                      : subtitleStyle === "gold"
                                      ? "text-[#E5C07B] scale-110 drop-shadow-[0_2px_8px_rgba(229,192,123,0.5)]"
                                      : subtitleStyle === "clean"
                                      ? "text-white underline decoration-[#E5C07B] decoration-2"
                                      : subtitleStyle === "minimal"
                                      ? "text-white border-b border-[#E5C07B] font-serif italic"
                                      : subtitleStyle === "emerald"
                                      ? "text-emerald-400 scale-110 drop-shadow-[0_2px_8px_rgba(52,211,153,0.6)]"
                                      : "text-rose-400 scale-110 drop-shadow-[0_2px_8px_rgba(244,63,94,0.6)]"
                                    : "text-white/80"
                                }`}
                              >
                                {word}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[9px] text-white/70 font-mono bg-black/60 px-1.5 py-0.5 rounded">
                      <span>1080x1920</span>
                      <span className="text-[#E5C07B]">Center Crop</span>
                    </div>
                  </div>
                ) : (
                  /* Framing Mode: Mode 2 = Canvas Fit with Blurred Letterbox */
                  <div className="absolute inset-y-1.5 left-[33%] w-[34%] rounded-lg border-2 border-emerald-400/80 bg-black/80 flex flex-col justify-between p-2 shadow-2xl transition-all duration-300">
                    <div className="flex items-center justify-between text-[9px] font-mono">
                      <span className="bg-emerald-500 text-black px-1.5 py-0.5 rounded font-bold shadow-sm">
                        FIT CANVAS
                      </span>
                      <span className="text-slate-300 bg-white/10 px-1 py-0.5 rounded">
                        DUAL SPEAKER
                      </span>
                    </div>

                    {/* Middle Letterbox with 100% full wide shot */}
                    <div className="my-auto w-full aspect-[16/9] bg-[#141A28] border border-white/20 rounded p-1 flex items-center justify-between relative overflow-hidden">
                      <div className="w-8 h-8 rounded-full bg-slate-700/80" />
                      <div className="text-[8px] font-mono text-emerald-400">Full 16:9 Letterbox</div>
                      <div className="w-8 h-8 rounded-full bg-[#1A2234] border border-[#E5C07B]" />
                    </div>

                    {/* Subtitle in the bottom vertical padded region */}
                    <div className="text-center my-1 px-1">
                      <div className="inline-block bg-black/90 px-2 py-1 rounded border border-white/10">
                        <div className="flex flex-wrap justify-center gap-1 text-[11px] font-bold">
                          {currentWords.map((word, wIdx) => (
                            <span
                              key={wIdx}
                              className={wIdx === wordIdx ? "text-[#E5C07B] scale-105" : "text-white/80"}
                            >
                              {word}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[9px] text-white/70 font-mono bg-black/60 px-1.5 py-0.5 rounded">
                      <span>1080x1920</span>
                      <span className="text-emerald-400">Zero Face Cropping</span>
                    </div>
                  </div>
                )}

                {/* Source Label */}
                <div className="absolute bottom-2 left-3 text-[10px] font-mono text-slate-500">
                  Naval Ravikant on Joe Rogan #1309
                </div>
              </div>

              {/* Authentic Gemini Narrative Arc Boundary (No Fake Scores) */}
              <div className="mt-4 p-3.5 rounded-xl bg-[#080A0F] border border-white/[0.06] space-y-2.5">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-slate-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#E5C07B]" />
                    <span>Gemini Narrative Hook Window: 04:12 - 04:48</span>
                  </span>
                  <span className="text-[#E5C07B] font-medium flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3 text-emerald-400" />
                    <span>Sentence Boundary Snapped</span>
                  </span>
                </div>

                {/* Multi-frequency waveform bars */}
                <div className="h-7 flex items-end gap-1 px-1">
                  {[24, 35, 45, 60, 75, 92, 98, 95, 88, 70, 55, 40, 65, 82, 94, 99, 92, 75, 60, 45, 30, 48, 62, 85, 90, 78, 60, 40].map((val, idx) => (
                    <div
                      key={idx}
                      style={{ height: `${val}%` }}
                      className={`flex-1 rounded-t transition-all ${
                        idx >= 5 && idx <= 17
                          ? "bg-[#E5C07B]"
                          : "bg-white/10"
                      }`}
                    />
                  ))}
                </div>
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>00:00 (Intro)</span>
                  <span className="text-slate-300">Autonomous pause alignment: ±0.04s precision</span>
                  <span>52:40 (Outro)</span>
                </div>
              </div>

            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
