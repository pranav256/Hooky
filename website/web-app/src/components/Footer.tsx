import { Zap } from "lucide-react";

export function Footer() {
  return (
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
  );
}
