export function Stats() {
  return (
    <section className="relative z-20 max-w-6xl mx-auto px-4 sm:px-8 mb-24">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 sm:p-8 rounded-2xl bg-[#10141E] border border-white/[0.08]">
        <div className="flex flex-col items-center text-center">
          <span className="text-3xl sm:text-4xl font-extrabold text-[#F8FAFC] font-mono">10x</span>
          <span className="text-xs text-slate-400 mt-1 font-medium">Faster than Manual Editing</span>
        </div>
        <div className="flex flex-col items-center text-center">
          <span className="text-3xl sm:text-4xl font-extrabold text-emerald-400 font-mono">$0 / mo</span>
          <span className="text-xs text-slate-400 mt-1 font-medium">100% Free MIT Open Source</span>
        </div>
        <div className="flex flex-col items-center text-center">
          <span className="text-3xl sm:text-4xl font-extrabold text-[#E5C07B] font-mono">240+ FPS</span>
          <span className="text-xs text-slate-400 mt-1 font-medium">CUDA / NVENC Transcode</span>
        </div>
        <div className="flex flex-col items-center text-center">
          <span className="text-3xl sm:text-4xl font-extrabold text-[#F8FAFC] font-mono">0 Cloud</span>
          <span className="text-xs text-slate-400 mt-1 font-medium">Complete Local Data Privacy</span>
        </div>
      </div>
    </section>
  );
}
