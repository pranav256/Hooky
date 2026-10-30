export function Footer() {
  return (
    <footer className="border-t border-white/[0.08] bg-[#06080C] py-12 px-4 sm:px-8 text-center text-xs text-slate-500">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-white">Hooky</span>
          <span>— Open-Source Autonomous AI Video Clipper</span>
        </div>

        <div className="flex items-center gap-6">
          <a
            href="https://github.com/pranav256/Hooky"
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-300 transition-colors"
          >
            GitHub Repository
          </a>
          <a
            href="https://github.com/pranav256/Hooky/blob/main/LICENSE"
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-300 transition-colors"
          >
            MIT License
          </a>
          <a
            href="https://ai.google.dev/"
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-300 transition-colors"
          >
            Gemini 2.0 Flash
          </a>
        </div>
      </div>
    </footer>
  );
}
