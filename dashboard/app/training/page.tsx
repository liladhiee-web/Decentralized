"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Flame,
  CheckCircle,
  Loader2,
  Globe,
  Layers,
  Cpu,
  ArrowRight,
  Database,
  Sparkles,
  Info,
  Sliders,
  CheckCircle2,
} from "lucide-react";

const MODEL_PRESETS = [
  { id: "Qwen/Qwen2.5-0.5B", name: "Qwen 2.5 (0.5B)", desc: "Lightweight, fastest training, ~2.5 GB VRAM" },
  { id: "TinyLlama/TinyLlama-1.1B-Chat-v1.0", name: "TinyLlama (1.1B)", desc: "Compact LLM, ~3.5 GB VRAM" },
  { id: "meta-llama/Llama-3.2-1B", name: "Llama 3.2 (1B)", desc: "Meta small instruct model, ~4.0 GB VRAM" },
  { id: "mistralai/Mistral-7B-v0.1", name: "Mistral (7B)", desc: "High capacity 7B, ~14 GB VRAM" },
];

const DATASET_PRESETS = [
  { id: "tatsu-lab/alpaca", name: "Alpaca (52k)", desc: "Classic instruction following demonstrations" },
  { id: "timdettmers/openassistant-guanaco", name: "OpenAssistant (9.8k)", desc: "Multi-turn human conversational data" },
  { id: "yahma/alpaca-cleaned", name: "Alpaca Cleaned", desc: "Curated deduplicated instructions" },
  { id: "databricks/databricks-dolly-15k", name: "Dolly (15k)", desc: "High quality human-generated QA pairs" },
];

export default function TrainingPage() {
  const [modelName, setModelName] = useState("Qwen/Qwen2.5-0.5B");
  const [datasetName, setDatasetName] = useState("tatsu-lab/alpaca");
  const [numBatches, setNumBatches] = useState(4);
  const [rank, setRank] = useState(16);
  const [alpha, setAlpha] = useState(32);
  const [epochs, setEpochs] = useState(3);
  const [lr, setLr] = useState("0.0002");
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; error: boolean; jobId?: string } | null>(null);

  // Generate batch slices preview
  const batchSlices = Array.from({ length: numBatches }, (_, i) => {
    const start = Math.round((i * 100) / numBatches);
    const end = Math.round(((i + 1) * 100) / numBatches);
    return {
      index: i + 1,
      slice: `train[${start}%:${end}%]`,
      percent: `${Math.round(100 / numBatches)}%`,
    };
  });

  async function handleLaunch(e: React.FormEvent) {
    e.preventDefault();
    if (!modelName.trim() || !datasetName.trim()) {
      setStatusMsg({ text: "Error: Please specify base model and dataset from Hugging Face", error: true });
      return;
    }

    setLoading(true);
    setStatusMsg(null);

    try {
      const res = await fetch("/api/v1/jobs/training/lora", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_name: modelName.trim(),
          dataset_name: datasetName.trim(),
          num_batches: Number(numBatches),
          is_distributed: true,
          lora_r: Number(rank),
          lora_alpha: Number(alpha),
          epochs: Number(epochs),
          learning_rate: parseFloat(lr),
          min_vram_mb: 4096,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setStatusMsg({
          text: `✓ Distributed Training Job Initialized! Divided into ${numBatches} discrete batches.`,
          error: false,
          jobId: data.id,
        });
      } else {
        setStatusMsg({ text: `Error: ${JSON.stringify(data)}`, error: true });
      }
    } catch (err: any) {
      setStatusMsg({ text: `Connection error: ${err.message}`, error: true });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Distributed Model Training Orchestrator</h1>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Hugging Face Hub
          </span>
        </div>
        <p className="text-sm text-gray-400 mt-1">
          Train parameter-efficient LoRA adapters by cutting Hugging Face datasets into distributed batches across community GPU nodes.
        </p>
      </div>

      {/* Hugging Face Hub Notice Card */}
      <div className="p-4 bg-gradient-to-r from-blue-900/20 to-indigo-900/20 border border-blue-500/20 rounded-xl flex items-start gap-3.5 text-xs text-gray-300">
        <Globe className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-white">Direct Hugging Face Hub Streaming: </span>
          Model uploads are no longer required or allowed. All base models and fine-tuning datasets are fetched on-demand directly from the open Hugging Face Hub. Community workers claim discrete batch shards, train on their GPU nodes, and the coordinator automatically joints all batches together into one unified trained model!
        </div>
      </div>

      <form onSubmit={handleLaunch} className="bg-[#111827]/80 border border-gray-800 rounded-2xl p-6 space-y-8">
        {/* Model Selection */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span>Base Model (Hugging Face Repository ID)</span>
            </label>
            <span className="text-[11px] text-gray-500">Zero file upload required</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {MODEL_PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setModelName(p.id)}
                className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                  modelName === p.id
                    ? "bg-blue-600/15 border-blue-500 text-white shadow-md shadow-blue-500/10"
                    : "bg-gray-900/60 border-gray-800 hover:border-gray-700 text-gray-300"
                }`}
              >
                <div className="font-semibold text-xs truncate">{p.name}</div>
                <div className="text-[10px] text-gray-500 truncate mt-0.5">{p.desc}</div>
              </button>
            ))}
          </div>

          <input
            type="text"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            placeholder="e.g. Qwen/Qwen2.5-0.5B or meta-llama/Llama-3.2-1B"
            className="w-full bg-gray-900 border border-gray-800 rounded-xl p-3 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
            required
          />
        </div>

        {/* Dataset Selection */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4 text-teal-400" />
              <span>Training Dataset (Hugging Face Repository ID)</span>
            </label>
            <span className="text-[11px] text-gray-500">Auto-partitioned into batches</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {DATASET_PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setDatasetName(p.id)}
                className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                  datasetName === p.id
                    ? "bg-teal-600/15 border-teal-500 text-white shadow-md shadow-teal-500/10"
                    : "bg-gray-900/60 border-gray-800 hover:border-gray-700 text-gray-300"
                }`}
              >
                <div className="font-semibold text-xs truncate">{p.name}</div>
                <div className="text-[10px] text-gray-500 truncate mt-0.5">{p.desc}</div>
              </button>
            ))}
          </div>

          <input
            type="text"
            value={datasetName}
            onChange={(e) => setDatasetName(e.target.value)}
            placeholder="e.g. tatsu-lab/alpaca or timdettmers/openassistant-guanaco"
            className="w-full bg-gray-900 border border-gray-800 rounded-xl p-3 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
            required
          />
        </div>

        {/* Distributed Batch Sharding Section */}
        <div className="p-5 bg-gray-900/50 border border-gray-800/90 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-amber-400" />
                <span>Distributed Batch Cutting & Partitioning</span>
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Divide training into discrete batches so multiple worker nodes can train in parallel.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400">Total Batches:</span>
              <div className="flex items-center gap-1 bg-black/40 p-1 rounded-lg border border-gray-800">
                {[2, 4, 8, 12].map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => setNumBatches(num)}
                    className={`px-3 py-1 rounded text-xs font-semibold transition-all cursor-pointer ${
                      numBatches === num ? "bg-amber-500 text-black shadow" : "text-gray-400 hover:text-white"
                    }`}
                  >
                    {num}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Visual Batch Cut Preview */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
            {batchSlices.map((b) => (
              <div
                key={b.index}
                className="p-3 bg-black/40 border border-amber-500/20 rounded-xl text-center space-y-1"
              >
                <div className="text-xs font-bold text-amber-400">Batch {b.index} of {numBatches}</div>
                <div className="text-[11px] font-mono text-gray-300">{b.slice}</div>
                <div className="text-[10px] text-gray-500">Partition size: {b.percent}</div>
              </div>
            ))}
          </div>

          <div className="text-[11px] text-gray-500 flex items-center gap-1.5 pt-1">
            <Info className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <span>
              Once all {numBatches} batches are trained by community workers, the coordinator automatically merges and joints all batch weights into one unified trained LoRA model.
            </span>
          </div>
        </div>

        {/* Hyperparameters Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 border-t border-gray-800/80 pt-6">
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-400">LoRA Rank (r)</label>
            <select
              value={rank}
              onChange={(e) => setRank(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl p-2.5 text-xs text-white"
            >
              <option value={8}>8 (Lightweight)</option>
              <option value={16}>16 (Recommended)</option>
              <option value={32}>32 (High Expressivity)</option>
              <option value={64}>64</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-400">LoRA Alpha</label>
            <input
              type="number"
              value={alpha}
              onChange={(e) => setAlpha(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl p-2.5 text-xs text-white font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-400">Epochs per Batch</label>
            <input
              type="number"
              min={1}
              max={10}
              value={epochs}
              onChange={(e) => setEpochs(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl p-2.5 text-xs text-white font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-400">Learning Rate</label>
            <input
              type="text"
              value={lr}
              onChange={(e) => setLr(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl p-2.5 text-xs text-white font-mono"
            />
          </div>
        </div>

        {/* Status Message & Action Link */}
        {statusMsg && (
          <div
            className={`p-4 rounded-xl text-xs space-y-2 border ${
              statusMsg.error
                ? "bg-red-500/10 text-red-400 border-red-500/20"
                : "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
            }`}
          >
            <div className="font-semibold">{statusMsg.text}</div>
            {!statusMsg.error && (
              <div className="pt-2 flex items-center gap-3">
                <Link
                  href="/workers"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-all shadow-md"
                >
                  <Cpu className="w-3.5 h-3.5" />
                  <span>Go to Workers Dashboard & Task Bar</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <span className="text-gray-400 text-[11px]">
                  Batch shards are now available for worker nodes to claim and train!
                </span>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between pt-4 border-t border-gray-800/80">
          <div className="text-xs text-gray-500">
            Divides dataset into {numBatches} batch shards for decentralized community execution.
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white font-semibold rounded-xl text-xs transition-all shadow-lg shadow-amber-500/20 cursor-pointer disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Flame className="w-4 h-4" />}
            <span>Launch Distributed Training ({numBatches} Batches)</span>
          </button>
        </div>
      </form>
    </div>
  );
}
