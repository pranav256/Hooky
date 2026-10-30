import { Sparkles, Radio, ShieldCheck, Film, Crop } from "lucide-react";

export function Pipeline() {
  return (
    <section id="pipeline" className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 mb-28 scroll-mt-24">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#10141E] border border-[#E5C07B]/20 text-[#E5C07B] text-xs font-medium uppercase tracking-wider mb-4">
          <Film className="w-3.5 h-3.5 text-[#E5C07B]" /> Modular Pipeline Engine
        </div>
        <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#F8FAFC]">
          Engineered for Clean Execution
        </h2>
        <p className="text-sm text-slate-400 mt-2">
          Driven cleanly by CLI configs, faster-whisper, and your local GPU. Zero cloud fees or telemetry.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Gemini Hook Analysis */}
        <div className="p-7 rounded-2xl bg-[#10141E] border border-white/[0.08] hover:border-[#E5C07B]/30 transition-all flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-[#171D2B] border border-white/10 flex items-center justify-center text-[#E5C07B] mb-5">
              <Sparkles className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-[#F8FAFC] mb-2.5">Gemini 2.0 Semantic Hooking</h3>
            <p className="text-xs text-slate-400 leading-relaxed mb-6">
              Gemini analyzes transcript pacing and emotional climax to extract standalone narrative segments (15s–75s). Never guesses with artificial virality formulas—it targets coherent thoughts that hook viewers.
            </p>
          </div>
          <div className="p-3 rounded-xl bg-[#080A0F] border border-white/5 font-mono text-xs text-emerald-400">
            ✓ Snaps boundaries to natural speech pauses
          </div>
        </div>

        {/* Framing & Tracking Representation */}
        <div className="p-7 rounded-2xl bg-[#10141E] border border-white/[0.08] hover:border-[#E5C07B]/30 transition-all flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-[#171D2B] border border-white/10 flex items-center justify-center text-[#E5C07B] mb-5">
              <Crop className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-[#F8FAFC] mb-2.5">Smart Framing &amp; Speaker Tracking</h3>
            <p className="text-xs text-slate-400 leading-relaxed mb-6">
              Supports two automated vertical layouts: close-up single speaker portrait cropping, and dual-layer ambient blur canvas that keeps two-person podcast interviews 100% visible with zero head cropping.
            </p>
          </div>
          <div className="p-3 rounded-xl bg-[#080A0F] border border-white/5 font-mono text-xs text-slate-300">
            --mode center (portrait) | --mode fit (wide)
          </div>
        </div>

        {/* Anti-Ban Instagram Poster */}
        <div className="p-7 rounded-2xl bg-[#10141E] border border-white/[0.08] hover:border-[#E5C07B]/30 transition-all flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-[#171D2B] border border-white/10 flex items-center justify-center text-[#E5C07B] mb-5">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-[#F8FAFC] mb-2.5">Anti-Ban Autonomous Publisher</h3>
            <p className="text-xs text-slate-400 leading-relaxed mb-6">
              Publishing in robotic bursts triggers social spam filters. Hooky implements randomized human cooldown jitter (30m–2h) and state checkpoint recovery to protect your channels completely.
            </p>
          </div>
          <div className="p-3 rounded-xl bg-[#080A0F] border border-white/5 font-mono text-xs text-emerald-400">
            ✓ Randomized Jitter: ~45m Cooldown
          </div>
        </div>
      </div>
    </section>
  );
}
