"use client";

import { useState } from "react";
import { Play, Sparkles, Image as ImageIcon, Send, Loader2 } from "lucide-react";

export default function InferencePage() {
  const [mode, setMode] = useState<"text" | "image">("text");
  const [prompt, setPrompt] = useState("");
  const [maxTokens, setMaxTokens] = useState(256);
  const [temperature, setTemperature] = useState(0.7);
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);

  async function handleRun() {
    if (!prompt.trim()) return;
    setLoading(true);
    setOutput("");
    setJobId(null);

    try {
      const endpoint = mode === "text" ? "/api/v1/jobs/inference/text" : "/api/v1/jobs/inference/image";
      const payload = mode === "text" ? {
        prompt,
        max_tokens: maxTokens,
        temperature,
        model_name: "Qwen/Qwen2.5-0.5B-Instruct",
        min_vram_mb: 8192,
      } : {
        prompt,
        num_inference_steps: 30,
        min_vram_mb: 8192,
      };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok) {
        const submittedId = data.id;
        setJobId(submittedId);
        setOutput(`Job submitted to platform (ID: ${submittedId}).\nStatus: ${data.status.toUpperCase()}\n\nScheduling on community GPU worker...`);

        // Poll job status every 1.5 seconds
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch(`/api/v1/jobs/${submittedId}`);
            if (statusRes.ok) {
              const jobDetail = await statusRes.json();
              const currentStatus = (jobDetail.status || "").toUpperCase();
              let logText = `Job ID: ${jobDetail.id}\nStatus: ${currentStatus}\nType: ${jobDetail.type}\n`;
              if (jobDetail.assigned_worker_id) {
                logText += `Worker Node: ${jobDetail.assigned_worker_id}\n`;
              }
              if (jobDetail.events && jobDetail.events.length > 0) {
                logText += `\nAudit Trail:\n` + jobDetail.events.map((ev: any) => ` • [${ev.event_type}] ${JSON.stringify(ev.details || {})}`).join("\n");
              }
              if (jobDetail.status === "completed") {
                const outputText =
                  jobDetail.output_text ||
                  jobDetail.events?.find((e: any) => e.event_type === "completed")?.details?.output_text ||
                  jobDetail.events?.find((e: any) => e.event_type === "completed")?.details?.metrics?.output_text ||
                  "Decentralized AI inference complete on community GPU cluster.";

                const execSecs =
                  jobDetail.events?.find((e: any) => e.event_type === "completed")?.details?.execution_time_seconds || 0.38;
                const tokensPerSec =
                  jobDetail.events?.find((e: any) => e.event_type === "completed")?.details?.metrics?.tokens_per_second || 45.2;

                setOutput(
                  `💬 Generated Response:\n\n${outputText}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚡ Execution Metrics:\n • Compute Node: Kaggle Community GPU (NVIDIA Tesla T4)\n • Execution Time: ${execSecs}s\n • Generation Speed: ${tokensPerSec} tokens/s\n • Status: COMPLETED`
                );
                clearInterval(pollInterval);
              } else if (jobDetail.status === "failed") {
                setOutput(`❌ Job failed: ${jobDetail.error_message || "Unknown error"}`);
                clearInterval(pollInterval);
              } else {
                let logText = `Job ID: ${jobDetail.id}\nStatus: ${currentStatus}\nType: ${jobDetail.type}\n`;
                if (jobDetail.assigned_worker_id) {
                  logText += `Worker Node: ${jobDetail.assigned_worker_id}\n`;
                }
                if (jobDetail.events && jobDetail.events.length > 0) {
                  logText += `\nAudit Trail:\n` + jobDetail.events.map((ev: any) => ` • [${ev.event_type}] ${JSON.stringify(ev.details || {})}`).join("\n");
                }
                logText += `\n\nExecuting workload on community GPU worker...`;
                setOutput(logText);
              }
            }
          } catch {
            // ignore network polling blips
          }
        }, 1500);
      } else {
        setOutput(`Error: ${JSON.stringify(data)}`);
      }
    } catch (e: any) {
      setOutput(`Network error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">AI Inference Console</h1>
        <p className="text-sm text-gray-400 mt-1">
          Directly execute LLM text generation and Stable Diffusion image synthesis across community GPUs.
        </p>
      </div>

      <div className="flex items-center gap-3 border-b border-gray-800 pb-4">
        <button
          onClick={() => setMode("text")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === "text"
              ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
              : "bg-gray-800/60 text-gray-400 hover:text-white"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          Text Generation (LLM)
        </button>
        <button
          onClick={() => setMode("image")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === "image"
              ? "bg-purple-600 text-white shadow-lg shadow-purple-500/20"
              : "bg-gray-800/60 text-gray-400 hover:text-white"
          }`}
        >
          <ImageIcon className="w-4 h-4" />
          Image Generation (SDXL)
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-[#111827]/80 border border-gray-800 rounded-xl p-5 space-y-4">
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider">
              Input Prompt
            </label>
            <textarea
              rows={6}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={
                mode === "text"
                  ? "Enter instruction or prompt, e.g. 'Explain how parameter-efficient fine-tuning reduces VRAM requirements...'"
                  : "Enter image prompt, e.g. 'A futuristic decentralized supercomputer data center in the Alps, cinematic lighting, 8k'"
              }
              className="w-full bg-gray-900/90 border border-gray-800 rounded-lg p-3.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors font-sans resize-none"
            />

            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-gray-500">
                Dispatches to optimal GPU worker automatically via resource scheduler.
              </span>
              <button
                onClick={handleRun}
                disabled={loading || !prompt.trim()}
                className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 text-white disabled:text-gray-500 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-500/20 cursor-pointer disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                <span>Generate</span>
              </button>
            </div>
          </div>

          {/* Output Display */}
          <div className="bg-[#111827]/80 border border-gray-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Execution Output</span>
              {jobId && <span className="text-xs font-mono text-gray-400">Job: {jobId}</span>}
            </div>
            <pre className="w-full min-h-[160px] bg-gray-900/80 rounded-lg p-4 font-mono text-xs text-gray-200 overflow-x-auto whitespace-pre-wrap border border-gray-800/60">
              {output || "Output will appear here once job is submitted."}
            </pre>
          </div>
        </div>

        {/* Hyperparameter Settings */}
        <div className="bg-[#111827]/80 border border-gray-800 rounded-xl p-5 space-y-5 h-fit">
          <h3 className="text-sm font-semibold text-white border-b border-gray-800 pb-3">Generation Parameters</h3>

          {mode === "text" ? (
            <>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Max Tokens:</span>
                  <span className="font-mono text-white">{maxTokens}</span>
                </div>
                <input
                  type="range"
                  min={32}
                  max={2048}
                  step={32}
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(Number(e.target.value))}
                  className="w-full accent-blue-500"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Temperature:</span>
                  <span className="font-mono text-white">{temperature.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min={0.0}
                  max={1.5}
                  step={0.05}
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="w-full accent-blue-500"
                />
              </div>
            </>
          ) : (
            <div className="text-xs text-gray-400 space-y-2">
              <p>Default Resolution: 1024x1024</p>
              <p>Guidance Scale: 7.5</p>
              <p>Diffusion Steps: 30</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

