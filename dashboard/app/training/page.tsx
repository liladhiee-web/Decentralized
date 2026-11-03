"use client";

import { useState } from "react";
import { Flame, CheckCircle, Loader2 } from "lucide-react";

export default function TrainingPage() {
  const [modelName, setModelName] = useState("mistralai/Mistral-7B-v0.1");
  const [datasetId, setDatasetId] = useState("");
  const [rank, setRank] = useState(16);
  const [alpha, setAlpha] = useState(32);
  const [epochs, setEpochs] = useState(3);
  const [lr, setLr] = useState("0.0002");
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  async function handleLaunch(e: React.FormEvent) {
    e.preventDefault();
    if (!datasetId.trim()) {
      setStatusMsg("Error: Please provide a valid Dataset UUID");
      return;
    }

    setLoading(true);
    setStatusMsg(null);

    try {
      const res = await fetch("/api/v1/jobs/training/lora", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_name: modelName,
          dataset_id: datasetId,
          lora_r: Number(rank),
          lora_alpha: Number(alpha),
          epochs: Number(epochs),
          learning_rate: parseFloat(lr),
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setStatusMsg(`✓ LoRA Fine-Tuning Job Dispatched! Job ID: ${data.id}`);
      } else {
        setStatusMsg(`Error: ${JSON.stringify(data)}`);
      }
    } catch (err: any) {
      setStatusMsg(`Connection error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">LoRA Fine-Tuning Orchestrator</h1>
        <p className="text-sm text-gray-400 mt-1">
          Train parameter-efficient low-rank adaptation matrices on community GPU compute nodes.
        </p>
      </div>

      <form onSubmit={handleLaunch} className="bg-[#111827]/80 border border-gray-800 rounded-xl p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider">
              Base Model Repository / Manifest
            </label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-blue-500"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider">
              Dataset UUID
            </label>
            <input
              type="text"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
              className="w-full bg-gray-900 border border-gray-800 rounded-lg p-3 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 border-t border-gray-800/80 pt-6">
          <div className="space-y-2">
            <label className="block text-xs text-gray-400">LoRA Rank (r)</label>
            <select
              value={rank}
              onChange={(e) => setRank(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-800 rounded-lg p-2.5 text-sm text-white"
            >
              <option value={8}>8</option>
              <option value={16}>16 (Standard)</option>
              <option value={32}>32</option>
              <option value={64}>64</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-xs text-gray-400">LoRA Alpha</label>
            <input
              type="number"
              value={alpha}
              onChange={(e) => setAlpha(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-800 rounded-lg p-2.5 text-sm text-white"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-xs text-gray-400">Epochs</label>
            <input
              type="number"
              min={1}
              max={10}
              value={epochs}
              onChange={(e) => setEpochs(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-800 rounded-lg p-2.5 text-sm text-white"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-xs text-gray-400">Learning Rate</label>
            <input
              type="text"
              value={lr}
              onChange={(e) => setLr(e.target.value)}
              className="w-full bg-gray-900 border border-gray-800 rounded-lg p-2.5 text-sm text-white font-mono"
            />
          </div>
        </div>

        {statusMsg && (
          <div className={`p-4 rounded-lg text-xs font-mono ${statusMsg.startsWith("✓") ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
            {statusMsg}
          </div>
        )}

        <div className="flex items-center justify-end pt-4">
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white font-semibold rounded-lg text-sm transition-all shadow-lg shadow-amber-500/20 cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Flame className="w-4 h-4" />}
            <span>Launch LoRA Fine-Tuning Run</span>
          </button>
        </div>
      </form>
    </div>
  );
}
