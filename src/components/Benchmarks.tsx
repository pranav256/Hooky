export function Benchmarks() {
  return (
    <section id="benchmarks" className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 mb-28 scroll-mt-24">
      <div className="text-center max-w-2xl mx-auto mb-12">
        <h2 className="text-3xl font-bold text-[#F8FAFC]">Hardware Benchmarks</h2>
        <p className="text-sm text-slate-400 mt-2">Tested on NVIDIA RTX, Apple Silicon Metal, and Multi-Core CPU:</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono">
        <div className="p-6 rounded-2xl bg-[#10141E] border border-white/[0.08]">
          <span className="text-[11px] text-slate-400 block mb-1">NVIDIA NVENC (GPU)</span>
          <span className="text-3xl font-bold text-white block">240+ FPS</span>
          <span className="text-xs text-emerald-400 mt-2 block">1080x1920 60p Transcode</span>
        </div>
        <div className="p-6 rounded-2xl bg-[#10141E] border border-white/[0.08]">
          <span className="text-[11px] text-slate-400 block mb-1">FASTER-WHISPER</span>
          <span className="text-3xl font-bold text-white block">int8 / fp16</span>
          <span className="text-xs text-[#E5C07B] mt-2 block">~3.2s per 10m audio</span>
        </div>
        <div className="p-6 rounded-2xl bg-[#10141E] border border-white/[0.08]">
          <span className="text-[11px] text-slate-400 block mb-1">RAM OVERHEAD</span>
          <span className="text-3xl font-bold text-white block">&lt; 1.4 GB</span>
          <span className="text-xs text-slate-300 mt-2 block">Auto-memory cleanup</span>
        </div>
        <div className="p-6 rounded-2xl bg-[#10141E] border border-white/[0.08]">
          <span className="text-[11px] text-slate-400 block mb-1">PRICING</span>
          <span className="text-3xl font-bold text-emerald-400 block">$0 / mo</span>
          <span className="text-xs text-slate-300 mt-2 block">100% Free MIT License</span>
        </div>
      </div>
    </section>
  );
}
