import { Database, CheckCircle2, Globe, Sparkles, ShieldCheck } from "lucide-react";

export const revalidate = 5;

export default function ModelsPage() {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">AI Models & Fine-Tuning Datasets</h1>
        <p className="text-sm text-gray-400 mt-1">
          Open ecosystem powered directly by the Hugging Face Hub with zero local storage requirements.
        </p>
      </div>

      {/* Zero-Storage Hugging Face Notice Card */}
      <div className="p-6 bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-blue-500/20 rounded-xl flex items-start gap-4">
        <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-lg">
          <Globe className="w-5 h-5" />
        </div>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-white">Direct Hugging Face Hub Integration</h3>
            <span className="text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
              Zero Local Storage Overhead
            </span>
          </div>
          <p className="text-xs text-gray-400 max-w-2xl leading-relaxed">
            Manual model and dataset file uploads are no longer required or allowed. All base models (LLMs, Diffusion, Audio, Video) and training datasets are fetched on-demand directly from the open Hugging Face Hub. Workers slice datasets into distributed batches, train on their GPU nodes, and stream weights back to the cluster.
          </p>
          <div className="font-mono text-xs text-blue-300 bg-gray-950/80 px-4 py-2.5 rounded-lg border border-gray-800 space-y-1">
            <div>• Base Models: Enter any repository ID from huggingface.co (e.g. Qwen/Qwen2.5-0.5B, TinyLlama/TinyLlama-1.1B)</div>
            <div>• Training Datasets: Enter any dataset repository (e.g. tatsu-lab/alpaca, timdettmers/openassistant-guanaco)</div>
          </div>
        </div>
      </div>

      {/* Popular Supported Models Grid */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Popular Hugging Face Base Models</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="p-5 bg-[#111827]/80 border border-gray-800 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">LLM</span>
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> HF Hub Ready
              </span>
            </div>
            <h3 className="font-bold text-white text-base">Qwen/Qwen2.5-0.5B</h3>
            <p className="text-xs text-gray-400">490M parameters, lightweight LoRA target, high throughput</p>
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-500">
              <span>Required VRAM: 2.5 GB</span>
              <span>PEFT / LoRA</span>
            </div>
          </div>

          <div className="p-5 bg-[#111827]/80 border border-gray-800 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">LLM</span>
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> HF Hub Ready
              </span>
            </div>
            <h3 className="font-bold text-white text-base">TinyLlama/TinyLlama-1.1B-Chat-v1.0</h3>
            <p className="text-xs text-gray-400">1.1B parameters, 3T tokens pre-trained, compact architecture</p>
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-500">
              <span>Required VRAM: 3.5 GB</span>
              <span>PEFT / LoRA</span>
            </div>
          </div>

          <div className="p-5 bg-[#111827]/80 border border-gray-800 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">LLM</span>
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> HF Hub Ready
              </span>
            </div>
            <h3 className="font-bold text-white text-base">meta-llama/Llama-3.2-1B</h3>
            <p className="text-xs text-gray-400">1.23B parameters, 128k context window, state-of-the-art small LLM</p>
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-500">
              <span>Required VRAM: 4.0 GB</span>
              <span>Transformers</span>
            </div>
          </div>
        </div>
      </div>

      {/* Popular Datasets Grid */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Supported Fine-Tuning Datasets (Hugging Face)</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="p-5 bg-[#111827]/80 border border-gray-800 rounded-xl space-y-3">
            <span className="text-xs font-mono text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded">Instruction</span>
            <h3 className="font-bold text-white text-base">tatsu-lab/alpaca</h3>
            <p className="text-xs text-gray-400">52,000 instruction-following demonstrations for fine-tuning LLMs</p>
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-500">
              <span>52k Samples</span>
              <span>Auto-Partitioning</span>
            </div>
          </div>

          <div className="p-5 bg-[#111827]/80 border border-gray-800 rounded-xl space-y-3">
            <span className="text-xs font-mono text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded">Conversational</span>
            <h3 className="font-bold text-white text-base">timdettmers/openassistant-guanaco</h3>
            <p className="text-xs text-gray-400">OASST1 human assistant dialogue multi-turn training data</p>
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-500">
              <span>9.8k Dialogues</span>
              <span>Auto-Partitioning</span>
            </div>
          </div>

          <div className="p-5 bg-[#111827]/80 border border-gray-800 rounded-xl space-y-3">
            <span className="text-xs font-mono text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded">Knowledge</span>
            <h3 className="font-bold text-white text-base">databricks/databricks-dolly-15k</h3>
            <p className="text-xs text-gray-400">15,000 curated high-quality employee instruction pairs</p>
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-500">
              <span>15k Records</span>
              <span>Auto-Partitioning</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
