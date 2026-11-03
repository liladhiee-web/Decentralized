import "./globals.css";
import Link from "next/link";
import { Cpu, Server, Play, Flame, Database, ListFilter, ShieldCheck, HardDrive } from "lucide-react";

export const metadata = {
  title: "CloudAI - Decentralized GPU Compute Platform",
  description: "Community-powered third-party GPU cloud for AI inference and distributed LoRA fine-tuning",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-[#090d16] text-gray-100 antialiased">
        {/* Left Navigation Sidebar */}
        <aside className="w-64 border-r border-gray-800/80 bg-[#0c121e]/90 backdrop-blur-md flex flex-col fixed inset-y-0 z-50">
          <div className="h-16 flex items-center px-6 border-b border-gray-800/60 gap-3">
            <div className="p-2 bg-gradient-to-tr from-blue-600 to-indigo-500 rounded-lg shadow-lg shadow-blue-500/20">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-wide text-white">CloudAI</span>
              <span className="text-[10px] block font-mono text-blue-400 tracking-wider uppercase">GPU Cloud</span>
            </div>
          </div>

          <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
            <Link
              href="/"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors"
            >
              <Cpu className="w-4 h-4 text-blue-400" />
              <span>Overview</span>
            </Link>
            <Link
              href="/marketplace"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors"
            >
              <Server className="w-4 h-4 text-emerald-400" />
              <span>GPU Marketplace</span>
            </Link>
            <Link
              href="/workers"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors"
            >
              <HardDrive className="w-4 h-4 text-cyan-400" />
              <span>Workers Dashboard</span>
            </Link>
            <Link
              href="/inference"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors"
            >
              <Play className="w-4 h-4 text-purple-400" />
              <span>AI Inference</span>
            </Link>
            <Link
              href="/training"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors"
            >
              <Flame className="w-4 h-4 text-amber-400" />
              <span>LoRA Fine-Tuning</span>
            </Link>
            <Link
              href="/models"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors"
            >
              <Database className="w-4 h-4 text-teal-400" />
              <span>Models & Datasets</span>
            </Link>
            <Link
              href="/jobs"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800/60 transition-colors"
            >
              <ListFilter className="w-4 h-4 text-pink-400" />
              <span>Job History</span>
            </Link>
          </nav>

          <div className="p-4 border-t border-gray-800/60 text-xs text-gray-500 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Zero-Trust Isolation
            </span>
            <span className="font-mono text-gray-400">v0.1.0</span>
          </div>
        </aside>

        {/* Main Content Viewport */}
        <div className="flex-1 flex flex-col ml-64 min-h-screen">
          <header className="h-16 border-b border-gray-800/80 bg-[#090d16]/80 backdrop-blur-md sticky top-0 z-40 px-8 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                Coordinator Online
              </div>
              <Link
                href="/workers"
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-colors"
              >
                <Cpu className="w-3.5 h-3.5" />
                <span>Connect Worker</span>
              </Link>
            </div>

            <div className="flex items-center gap-4">
              <div className="px-3 py-1.5 bg-gray-800/40 border border-gray-800 rounded-lg text-xs font-mono text-gray-300">
                Credits: <span className="font-bold text-emerald-400">10.0000</span>
              </div>
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-xs text-white">
                AI
              </div>
            </div>
          </header>

          <main className="flex-1 p-8 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

