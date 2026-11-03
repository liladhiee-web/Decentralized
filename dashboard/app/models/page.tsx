import { Database, FileCode, CheckCircle2, Shield, UploadCloud } from "lucide-react";

export const revalidate = 5;

export default function ModelsPage() {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">AI Models & Fine-Tuning Datasets</h1>
        <p className="text-sm text-gray-400 mt-1">
          Catalog of validated Safetensors model weights, base checkpoints, and training datasets.
        </p>
      </div>

      {/* CLI Upload Instructions Card */}
      <div className="p-6 bg-gradient-to-r from-blue-900/20 to-indigo-900/20 border border-blue-500/20 rounded-xl flex items-start gap-4">
        <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-lg">
          <UploadCloud className="w-5 h-5" />
        </div>
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-white">Direct-to-S3 Resumable Uploads</h3>
          <p className="text-xs text-gray-400 max-w-2xl">
            Large models (7B, 13B, 70B) and datasets stream directly to MinIO/S3 object storage using short-lived pre-signed URLs with SHA-256 integrity verification. Upload files using the CloudAI CLI:
          </p>
          <div className="font-mono text-xs text-emerald-400 bg-gray-950/80 px-4 py-2.5 rounded-lg border border-gray-800 space-y-1">
            <div>cloudai models upload ./models/llama3-8b.safetensors --name meta-llama-3-8b --vram 16384</div>
            <div>cloudai datasets upload ./data/alpaca_instruct.jsonl --name alpaca-instruct</div>
          </div>
        </div>
      </div>

      {/* Models Grid */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Supported Base Models</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="p-5 bg-[#111827]/80 border border-gray-800 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">LLM</span>
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Ready
              </span>
            </div>
            <h3 className="font-bold text-white text-base">meta-llama/Llama-3-8B-Instruct</h3>
            <p className="text-xs text-gray-400">8.03B parameters, Safetensors, native bfloat16</p>
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-500">
              <span>Required VRAM: 16 GB</span>
              <span>Transformers</span>
            </div>
          </div>

          <div className="p-5 bg-[#111827]/80 border border-gray-800 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">LLM</span>
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Ready
              </span>
            </div>
            <h3 className="font-bold text-white text-base">mistralai/Mistral-7B-v0.1</h3>
            <p className="text-xs text-gray-400">7.24B parameters, sliding window attention, LoRA target</p>
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-500">
              <span>Required VRAM: 14 GB</span>
              <span>PEFT / Accelerate</span>
            </div>
          </div>

          <div className="p-5 bg-[#111827]/80 border border-gray-800 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded">Diffusion</span>
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Ready
              </span>
            </div>
            <h3 className="font-bold text-white text-base">stabilityai/stable-diffusion-xl-base-1.0</h3>
            <p className="text-xs text-gray-400">3.5B parameters, 1024x1024 native latent diffusion</p>
            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-500">
              <span>Required VRAM: 12 GB</span>
              <span>Diffusers</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
