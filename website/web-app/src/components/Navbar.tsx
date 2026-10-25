import { Star, ArrowRight, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Navbar() {
  return (
    <header className="fixed top-4 left-0 right-0 z-50 px-4 sm:px-8">
      <div className="max-w-6xl mx-auto h-14 bg-[#111726]/90 backdrop-blur-md border border-white/[0.08] rounded-2xl px-5 flex items-center justify-between shadow-lg">
        <a href="#" className="flex items-center gap-2.5">
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
          <a href="#demo" className="hover:text-white transition-colors">Interactive Demo</a>
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
  );
}
