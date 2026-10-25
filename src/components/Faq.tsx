import { ChevronDown } from "lucide-react";

export function Faq() {
  const faqs = [
    {
      q: "Can I run Hooky without a dedicated GPU?",
      a: "Yes! Hooky auto-profiles your system on startup. If no NVIDIA CUDA GPU is found, it switches Whisper to int8 CPU mode and leverages multi-threaded CPU FFmpeg encoding.",
    },
    {
      q: "Does Google Gemini API cost money?",
      a: "Google Gemini 2.0 Flash has a generous free tier in Google AI Studio. Since Hooky passes only timestamps and text transcripts (not giant multi-gigabyte video files), token consumption is minimal and fits within free quotas.",
    },
    {
      q: "How does the smart video framing (center vs fit) work?",
      a: "Hooky provides two framing methods: --mode center applies a focused 1080x1920 crop on the primary speaker, while --mode fit preserves 100% of widescreen multi-speaker shots by centering the video over an ambient blurred background fill so no faces get cropped.",
    },
    {
      q: "How does the anti-ban Instagram queue keep accounts safe?",
      a: "Automated spammers get banned for fixed-interval posts. Hooky randomizes delays between uploads (configurable in .env between 30 mins and 2 hours), restricts uploads to active daylight hours (e.g. 9 AM – 10 PM), and tracks posted video IDs to prevent duplicates.",
    },
    {
      q: "Can I split long masterclasses or podcasts into Part 1, Part 2, etc.?",
      a: "Yes! Run ./hooky.sh parts <video.mp4> --part-duration 60. Hooky automatically calculates segment boundaries, burns sequential 'Part N' badges into the video header, and outputs clean 60-second vertical reels.",
    },
    {
      q: "Which subtitle styles are supported in Hooky?",
      a: "Hooky supports multiple subtitle presets including hormozi (bold uppercase with dynamic spoken word highlights), yellow (high-contrast yellow keyword highlights), and clean (modern minimalist with subtle background box). Run ./hooky.sh styles to preview them directly in your terminal.",
    },
  ];

  return (
    <section id="faq" className="relative z-20 max-w-4xl mx-auto px-4 sm:px-8 mb-24 scroll-mt-24">
      <div className="text-center mb-10">
        <h2 className="text-3xl font-bold text-[#F8FAFC]">Frequently Asked Questions</h2>
      </div>

      <div className="space-y-3.5 text-sm">
        {faqs.map((faq, idx) => (
          <details key={idx} className="p-5 rounded-xl bg-[#10141E] border border-white/[0.08] group cursor-pointer">
            <summary className="flex items-center justify-between font-medium text-white list-none">
              <span>{faq.q}</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
            </summary>
            <p className="mt-3 text-xs text-slate-400 leading-relaxed">
              {faq.a}
            </p>
          </details>
        ))}
      </div>
    </section>
  );
}
