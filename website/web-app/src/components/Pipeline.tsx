import { Sparkles, Radio, ShieldCheck, Film } from "lucide-react";

export function Pipeline() {
  return (
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
  );
}
