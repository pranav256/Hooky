import { Navbar } from "@/components/Navbar";
import { Hero } from "@/components/Hero";
import { Stats } from "@/components/Stats";
import { Pipeline } from "@/components/Pipeline";
import { TerminalStudio } from "@/components/TerminalStudio";
import { Benchmarks } from "@/components/Benchmarks";
import { Faq } from "@/components/Faq";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0B0F19] text-[#F3F4F6] font-sans selection:bg-[#3B82F6]/30 selection:text-white relative overflow-x-hidden">
      <Navbar />
      <main>
        <Hero />
        <Stats />
        <Pipeline />
        <TerminalStudio />
        <Benchmarks />
        <Faq />
      </main>
      <Footer />
    </div>
  );
}
