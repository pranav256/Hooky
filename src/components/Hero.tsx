"use client";

import { useState, useEffect } from "react";
import { Copy, Check, Sparkles, Sliders, Play, Pause, Flame, Volume2, VolumeX } from "lucide-react";
import { Button } from "@/components/ui/button";

const SCRIPT_WORDS = [
  ["SPECIFIC", "KNOWLEDGE", "CANNOT", "BE", "TAUGHT"],
  ["CODE", "AND", "MEDIA", "ARE", "PERMISSIONLESS", "LEVERAGE"],
  ["NEVER", "RENT", "OUT", "YOUR", "TIME"],
  ["DOPAMINE", "FOLLOWS", "ACTION", "NOT", "THOUGHT"],
  ["COMPOUNDING", "CREATES", "UNFAIR", "ADVANTAGES"],
];

export function Hero() {
  const [copied, setCopied] = useState(false);
  const [subtitleStyle, setSubtitleStyle] = useState<"hormozi" | "yellow" | "clean">("hormozi");
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

  return (
    <section id="demo" className="relative pt-32 pb-20 px-4 sm:px-8 overflow-hidden">
      {/* Soft ambient depth glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-[#3B82F6]/[0.05] blur-[140px] pointer-events-none rounded-full" />

      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          
          {/* Left Column: Value Proposition */}
          <div className="lg:col-span-6 flex flex-col items-start text-left">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#131926] border border-white/10 text-slate-300 text-xs font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5 text-[#3B82F6]" />
              <span>Google Gemini 2.0 Flash + Faster-Whisper</span>
            </div>

            <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight leading-[1.08] text-[#F8FAFC] mb-6">
              Turn Long Videos <br />
              Into Viral Shorts. <br />
              <span className="text-[#94A3B8] font-semibold text-3xl sm:text-4xl">100% Free &amp; Open Source.</span>
            </h1>

            <p className="text-[#94A3B8] text-base sm:text-lg max-w-xl leading-relaxed mb-8">
              Autonomous AI detects narrative hooks, applies clean 9:16 vertical framing, and burns animated Hormozi captions on your local GPU. Zero cloud fees. Zero lock-in.
            </p>

            {/* 1-Click Terminal Pill */}
            <div className="w-full sm:w-auto flex flex-col sm:flex-row items-stretch sm:items-center gap-3 p-1.5 rounded-2xl bg-[#131926] border border-white/10 backdrop-blur-md mb-8 group hover:border-[#3B82F6]/40 transition-all shadow-md">
              <div className="flex items-center gap-2.5 px-3 py-1 font-mono text-xs sm:text-sm text-slate-300">
                <span className="text-[#3B82F6] font-bold">$</span>
                <span className="truncate">git clone https://github.com/pranav256/Hooky.git &amp;&amp; ./hooky.sh</span>
              </div>
              <Button
                size="sm"
                className="shrink-0"
                onClick={handleCopy}
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </Button>
            </div>

            {/* Caption Style Switcher */}
            <div className="flex flex-col gap-2 pt-1">
              <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-[#3B82F6]" />
                <span>Live Subtitle Preset Selector:</span>
              </span>
              <div className="flex flex-wrap items-center gap-2">
                {(["hormozi", "yellow", "clean"] as const).map((style) => (
                  <button
                    key={style}
                    onClick={() => setSubtitleStyle(style)}
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

          {/* Right Column: Interactive 16:9 to 9:16 Visual Studio Preview */}
          <div className="lg:col-span-6 w-full">
            <div className="rounded-2xl bg-[#131926] border border-white/10 shadow-2xl p-5 relative overflow-hidden">
              
              {/* Studio Header Bar */}
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-white/[0.08] text-xs">
                <div className="flex items-center gap-2 text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-semibold text-white">Hooky Studio</span>
                  <span className="text-slate-500">•</span>
                  <span className="text-slate-400 font-mono">16:9 Master → 9:16 Vertical Crop</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsMuted(!isMuted)}
                    className="p-1 rounded-lg bg-[#0B0F19] border border-white/10 text-slate-400 hover:text-white transition-colors"
                  >
                    {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#0B0F19] border border-white/10 text-slate-300 hover:text-white font-mono text-[11px] transition-colors"
                  >
                    {isPlaying ? <Pause className="w-3 h-3 text-blue-400" /> : <Play className="w-3 h-3 text-emerald-400" />}
                    <span>{isPlaying ? "Live" : "Paused"}</span>
                  </button>
                </div>
              </div>

              {/* 16:9 Widescreen Video Frame with 9:16 Vertical Crop Window */}
              <div className="aspect-[16/9] w-full rounded-xl bg-[#0B0F19] border border-white/10 relative overflow-hidden flex items-center justify-center">
                <div className="absolute inset-0 bg-gradient-to-r from-slate-900 via-[#131a26] to-slate-900 opacity-90" />

                {/* Left Speaker / Host Silhouette */}
                <div className="absolute left-[18%] top-[28%] flex flex-col items-center opacity-40">
                  <div className="w-16 h-16 rounded-full bg-slate-700/80 mb-2" />
                  <div className="w-28 h-14 rounded-t-full bg-slate-800/80" />
                  <span className="text-[10px] font-mono text-slate-500 mt-1">Host</span>
                </div>

                {/* Right Speaker (Active Speaker) in center of 9:16 crop box */}
                <div className="absolute right-[32%] top-[25%] flex flex-col items-center">
                  <div className="w-18 h-18 rounded-full bg-[#1E293B] border border-blue-400/40 shadow-lg shadow-blue-500/10 mb-2 relative">
                    <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 border-2 border-[#131926]" />
                  </div>
                  <div className="w-32 h-16 rounded-t-full bg-[#1E293B] border-t border-blue-400/20" />
                  <span className="text-[10px] font-mono text-blue-400 mt-1 font-semibold">Guest Speaker</span>
                </div>

                {/* Dynamic 9:16 Vertical Crop Overlay Boundary */}
                <div className="absolute inset-y-2 left-[44%] w-[34%] rounded-lg border-2 border-[#3B82F6] bg-blue-500/[0.04] backdrop-blur-[0.5px] shadow-2xl flex flex-col justify-between p-2.5 transition-all duration-300">
                  {/* Top crop header */}
                  <div className="flex items-center justify-between text-[9px] font-mono">
                    <span className="bg-[#3B82F6] text-white px-1.5 py-0.5 rounded font-bold shadow-sm">
                      9:16 REEL
                    </span>
                    <span className="text-emerald-400 bg-black/60 px-1 py-0.5 rounded">
                      CENTER CROP
                    </span>
                  </div>

                  {/* Word-by-Word Kinetic Subtitle Overlay */}
                  <div className="text-center my-auto px-1">
                    <div className="inline-block bg-black/80 backdrop-blur-md px-2.5 py-1.5 rounded-lg border border-white/10 max-w-full">
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
                                    : subtitleStyle === "yellow"
                                    ? "text-amber-400 scale-110"
                                    : "text-sky-300 underline"
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

                  {/* Bottom Video Meta */}
                  <div className="flex items-center justify-between text-[9px] text-white/70 font-mono bg-black/50 px-1.5 py-0.5 rounded">
                    <span>1080x1920</span>
                    <span className="text-blue-300">60 FPS</span>
                  </div>
                </div>

                {/* Subtle Grid guides */}
                <div className="absolute bottom-2 left-3 text-[10px] font-mono text-slate-500">
                  Source: Naval Ravikant on Joe Rogan #1309
                </div>
              </div>

              {/* Waveform Retention Timeline */}
              <div className="mt-4 p-3 rounded-xl bg-[#0B0F19] border border-white/5 space-y-2">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Flame className="w-3.5 h-3.5 text-[#3B82F6]" />
                    AI Highlight Window: 04:12 - 04:48
                  </span>
                  <span className="text-emerald-400 font-semibold">Narrative Climax Hook</span>
                </div>

                {/* Multi-frequency waveform bars */}
                <div className="h-8 flex items-end gap-1 px-1">
                  {[24, 35, 45, 60, 75, 92, 98, 95, 88, 70, 55, 40, 65, 82, 94, 99, 92, 75, 60, 45, 30, 48, 62, 85, 90, 78, 60, 40].map((val, idx) => (
                    <div
                      key={idx}
                      style={{ height: `${val}%` }}
                      className={`flex-1 rounded-t transition-all ${
                        idx >= 5 && idx <= 17
                          ? "bg-[#3B82F6]"
                          : "bg-white/10"
                      }`}
                    />
                  ))}
                </div>
                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>00:00</span>
                  <span className="text-[#3B82F6]">Snaps to Sentence Pause</span>
                  <span>52:40</span>
                </div>
              </div>

            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
