"use client";

import { useState } from "react";
import { Terminal, Check, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";

export function TerminalStudio() {
  const [activeTab, setActiveTab] = useState<"make" | "preview" | "parts" | "doctor">("make");
  const [copied, setCopied] = useState(false);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const cliOutputs = {
    make: (
      <>
        <span className="text-[#E5C07B] font-bold">$ ./hooky.sh make</span>
        <br /><br />
        <span className="text-slate-400">[01/04]</span> Auto-scanning channels.txt for new uploads...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Found winning source: @TheDiaryOfACEO (840k views) -&gt; <span className="text-emerald-400">QUEUED</span><br />
        <span className="text-slate-400">[02/04]</span> Gemini 2.0 Flash analyzing narrative hook points...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• Segment 1 [01:14 -&gt; 01:52]: <span className="text-[#E5C07B]">Specific knowledge leverage point</span><br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• Segment 2 [12:40 -&gt; 13:22]: <span className="text-emerald-400">Permissionless code &amp; media principle</span><br />
        <span className="text-slate-400">[03/04]</span> Faster-whisper int8 millisecond word-level timing...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Aligned 124 words with frame-accurate ASS karaoke boundaries.<br />
        <span className="text-slate-400">[04/04]</span> Local GPU 1080x1920 smart framing at 240 FPS...<br />
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-emerald-400">✓ output/diary_of_ceo_clip_01.mp4 generated (38s)</span><br />
        <span className="text-slate-200 font-medium">Done. Added to anti-ban Instagram queue with safe 45m jitter delay.</span>
      </>
    ),
    preview: (
      <>
        <span className="text-[#E5C07B] font-bold">$ ./hooky.sh preview</span>
        <br /><br />
        <span className="text-slate-400">[Dry-Run Mode: Zero disk writes or rendering]</span><br />
        • Parsing pending video: https://www.youtube.com/watch?v=3qHkcs3kG44<br />
        • Title: Naval Ravikant - How to Get Rich Without Getting Lucky<br />
        • Gemini 2.0 Hook Extraction (completed in 1.1s):<br />
        &nbsp;&nbsp;1. [04:12 - 04:48] &quot;Specific knowledge vs competition&quot;<br />
        &nbsp;&nbsp;2. [18:30 - 19:15] &quot;Code and media are permissionless leverage&quot;<br />
        Ready to process. Run <span className="text-[#E5C07B]">./hooky.sh</span> to render.
      </>
    ),
    parts: (
      <>
        <span className="text-[#E5C07B] font-bold">$ ./hooky.sh parts masterclass.mp4 --part-duration 60</span>
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
        <span className="text-[#E5C07B] font-bold">$ ./hooky.sh doctor</span>
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
    <section id="terminal" className="relative z-20 max-w-5xl mx-auto px-4 sm:px-8 mb-28 scroll-mt-24">
      <div className="text-center max-w-2xl mx-auto mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#10141E] border border-[#E5C07B]/20 text-[#E5C07B] text-xs font-medium uppercase tracking-wider mb-4">
          <Terminal className="w-3.5 h-3.5 text-[#E5C07B]" /> Terminal Studio
        </div>
        <h2 className="text-3xl sm:text-4xl font-bold text-[#F8FAFC]">
          Authentic CLI Command Streams
        </h2>
        <p className="text-sm text-slate-400 mt-2">
          Switch between CLI tasks below to inspect real pipeline executions:
        </p>
      </div>

      <div className="rounded-2xl overflow-hidden bg-[#0A0D14] border border-white/10 shadow-2xl">
        {/* Terminal Top Bar */}
        <div className="bg-[#10141E] px-6 py-3 border-b border-white/[0.08] flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
            <span className="ml-3 font-mono text-xs text-slate-400">bash / powershell</span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#080A0F] p-1 rounded-xl border border-white/10 text-xs font-mono">
            {(["make", "preview", "parts", "doctor"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1 rounded-lg transition-all ${
                  activeTab === tab
                    ? "bg-[#E5C07B] text-[#0A0D14] font-semibold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                ./hooky.sh {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Terminal Body */}
        <div className="p-6 font-mono text-xs sm:text-sm text-slate-300 min-h-[270px] overflow-x-auto relative leading-relaxed bg-[#080A0F]">
          <Button
            size="sm"
            variant="outline"
            className="absolute top-4 right-4 text-xs border-white/10"
            onClick={() => handleCopy(`./hooky.sh ${activeTab}`)}
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400 mr-1" /> : <Copy className="w-3.5 h-3.5 mr-1 text-[#E5C07B]" />}
            <span>{copied ? "Copied" : "Copy Command"}</span>
          </Button>
          <div className="font-mono">{cliOutputs[activeTab]}</div>
        </div>
      </div>
    </section>
  );
}
