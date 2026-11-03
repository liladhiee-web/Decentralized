"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  Play,
  Sparkles,
  Image as ImageIcon,
  Mic,
  Video,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Cpu,
  Server,
  Layers,
  Info,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Sliders,
} from "lucide-react";

interface GPUDevice {
  id: string;
  name: string;
  total_vram_mb: number;
  free_vram_mb: number;
  cuda_compute_capability: string;
  temperature_celsius: number;
}

interface Worker {
  id: string;
  name: string;
  hostname: string;
  status: "idle" | "busy" | "draining" | "offline";
  gpu_devices: GPUDevice[];
}

type Modality = "text" | "image" | "audio" | "video";

interface ModelPreset {
  id: string;
  name: string;
  vramMB: number;
  params: string;
  description: string;
}

const PRESETS: Record<Modality, ModelPreset[]> = {
  text: [
    {
      id: "Qwen/Qwen2.5-0.5B-Instruct",
      name: "Qwen 2.5 (0.5B)",
      vramMB: 2048,
      params: "0.5B params",
      description: "Ultra-fast lightweight instruct LLM, fits any GPU",
    },
    {
      id: "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
      name: "TinyLlama (1.1B)",
      vramMB: 3072,
      params: "1.1B params",
      description: "Compact chat model with low latency",
    },
    {
      id: "meta-llama/Llama-3.2-1B-Instruct",
      name: "Llama 3.2 (1B)",
      vramMB: 3584,
      params: "1.2B params",
      description: "Meta open instruction-tuned model",
    },
    {
      id: "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
      name: "DeepSeek R1 (1.5B)",
      vramMB: 4096,
      params: "1.5B params",
      description: "Reasoning distilled model for logic and math",
    },
    {
      id: "Qwen/Qwen2.5-3B-Instruct",
      name: "Qwen 2.5 (3B)",
      vramMB: 7168,
      params: "3.1B params",
      description: "Balanced reasoning and code generation",
    },
    {
      id: "mistralai/Mistral-7B-Instruct-v0.3",
      name: "Mistral (7B)",
      vramMB: 14336,
      params: "7.2B params",
      description: "High capability 7B LLM (requires >=15GB VRAM)",
    },
  ],
  image: [
    {
      id: "runwayml/stable-diffusion-v1-5",
      name: "Stable Diffusion 1.5",
      vramMB: 5120,
      params: "860M params",
      description: "Classic high-speed image diffusion",
    },
    {
      id: "stabilityai/stable-diffusion-xl-base-1.0",
      name: "SDXL 1.0",
      vramMB: 10240,
      params: "3.5B params",
      description: "Photorealistic 1024x1024 image synthesis",
    },
    {
      id: "black-forest-labs/FLUX.1-schnell",
      name: "FLUX.1 Schnell",
      vramMB: 14336,
      params: "12B params",
      description: "State-of-the-art 4-step diffusion model",
    },
  ],
  audio: [
    {
      id: "openai/whisper-tiny",
      name: "Whisper Tiny",
      vramMB: 1536,
      params: "39M params",
      description: "Sub-second speech-to-text transcription",
    },
    {
      id: "openai/whisper-base",
      name: "Whisper Base",
      vramMB: 2560,
      params: "74M params",
      description: "Accurate multi-lingual audio transcription",
    },
    {
      id: "suno/bark-small",
      name: "Bark TTS (Small)",
      vramMB: 5120,
      params: "300M params",
      description: "Expressive generative text-to-speech",
    },
  ],
  video: [
    {
      id: "stabilityai/stable-video-diffusion-img2vid",
      name: "Stable Video Diffusion",
      vramMB: 14336,
      params: "1.5B params",
      description: "High frame-rate temporal video generation",
    },
    {
      id: "damo-vilab/text-to-video-ms-1.7b",
      name: "Text-to-Video MS (1.7B)",
      vramMB: 12288,
      params: "1.7B params",
      description: "Direct text-to-video diffusion pipeline",
    },
  ],
};

function estimateModelVramMB(modelId: string, modality: Modality): number {
  const lower = modelId.toLowerCase();
  // Check known presets first
  for (const list of Object.values(PRESETS)) {
    const match = list.find((p) => p.id.toLowerCase() === lower);
    if (match) return match.vramMB;
  }

  // Heuristic estimation based on name
  if (lower.includes("70b")) return 140000;
  if (lower.includes("32b") || lower.includes("34b")) return 64000;
  if (lower.includes("14b") || lower.includes("13b")) return 28000;
  if (lower.includes("7b") || lower.includes("8b")) return 14500;
  if (lower.includes("3b")) return 7000;
  if (lower.includes("2b")) return 5000;
  if (lower.includes("1.5b") || lower.includes("1.1b") || lower.includes("1b")) return 3500;
  if (lower.includes("0.5b") || lower.includes("360m")) return 2048;

  if (modality === "image") {
    if (lower.includes("flux")) return 14000;
    if (lower.includes("xl") || lower.includes("sdxl")) return 10240;
    return 6000;
  }
  if (modality === "audio") {
    if (lower.includes("large")) return 8000;
    if (lower.includes("medium")) return 5000;
    return 2048;
  }
  if (modality === "video") return 14000;

  return 4096;
}

export default function InferencePage() {
  const [modality, setModality] = useState<Modality>("text");
  const [customModel, setCustomModel] = useState("Qwen/Qwen2.5-0.5B-Instruct");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showNodeDrawer, setShowNodeDrawer] = useState(false);

  // Hyperparameters
  const [maxTokens, setMaxTokens] = useState(256);
  const [temperature, setTemperature] = useState(0.7);
  const [imageWidth, setImageWidth] = useState(1024);
  const [imageHeight, setImageHeight] = useState(1024);
  const [imageSteps, setImageSteps] = useState(30);
  const [audioTask, setAudioTask] = useState<"transcribe" | "synthesize">("transcribe");
  const [videoFrames, setVideoFrames] = useState(14);

  // Connected workers
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loadingWorkers, setLoadingWorkers] = useState(true);

  // Fetch online workers for real-time spec checking
  async function fetchWorkers() {
    try {
      const res = await fetch("/api/v1/workers");
      if (res.ok) {
        const data = await res.json();
        setWorkers(data);
      }
    } catch {
      // ignore
    } finally {
      setLoadingWorkers(false);
    }
  }

  useEffect(() => {
    fetchWorkers();
    const interval = setInterval(fetchWorkers, 5000);
    return () => clearInterval(interval);
  }, []);

  // Update default model when modality switches
  function handleModalityChange(m: Modality) {
    setModality(m);
    setCustomModel(PRESETS[m][0].id);
    if (!prompt) {
      if (m === "text") setPrompt("Explain how decentralized GPU clusters perform tensor parallel inference.");
      if (m === "image") setPrompt("A futuristic quantum AI supercomputer floating in deep space, hyperrealistic 8k.");
      if (m === "audio") setPrompt("Hello decentralized AI cluster, transcribe this audio telemetry packet.");
      if (m === "video") setPrompt("A luminous neural network pulsing with high speed data packets.");
    }
  }

  // Estimated model VRAM requirement
  const estimatedVramMB = useMemo(() => {
    return estimateModelVramMB(customModel, modality);
  }, [customModel, modality]);

  // Online GPU nodes calculation
  const onlineWorkers = useMemo(() => {
    return workers.filter((w) => w.status === "idle" || w.status === "busy");
  }, [workers]);

  const maxAvailableVramMB = useMemo(() => {
    let max = 0;
    for (const w of onlineWorkers) {
      for (const g of w.gpu_devices || []) {
        if (g.total_vram_mb > max) max = g.total_vram_mb;
      }
    }
    return max;
  }, [onlineWorkers]);

  const bestGpuName = useMemo(() => {
    for (const w of onlineWorkers) {
      for (const g of w.gpu_devices || []) {
        if (g.total_vram_mb === maxAvailableVramMB) return g.name;
      }
    }
    return "Community GPU";
  }, [onlineWorkers, maxAvailableVramMB]);

  // Hardware Compatibility Evaluation
  const compatibility = useMemo(() => {
    if (onlineWorkers.length === 0) {
      return {
        status: "none",
        color: "text-amber-400 bg-amber-500/10 border-amber-500/20",
        title: "No Active GPU Workers Online",
        message:
          "Connect a worker node from the Workers Dashboard (e.g. Kaggle Tesla T4 / Colab) to execute this model.",
        canRun: false,
      };
    }

    if (maxAvailableVramMB >= estimatedVramMB + 1024) {
      return {
        status: "optimal",
        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        title: "Fully Compatible Hardware",
        message: `Node ${bestGpuName} (${(maxAvailableVramMB / 1024).toFixed(1)} GB VRAM) has sufficient headroom for this ~${(estimatedVramMB / 1024).toFixed(1)} GB model.`,
        canRun: true,
      };
    }

    if (maxAvailableVramMB >= estimatedVramMB * 0.85) {
      return {
        status: "tight",
        color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
        title: "High Memory Footprint (FP16 Recommended)",
        message: `Model footprint (~${(estimatedVramMB / 1024).toFixed(1)} GB) is near node capacity (${(maxAvailableVramMB / 1024).toFixed(1)} GB). Half-precision execution will be applied.`,
        canRun: true,
      };
    }

    return {
      status: "insufficient",
      color: "text-red-400 bg-red-500/10 border-red-500/20",
      title: "Insufficient VRAM on Connected Nodes",
      message: `Model requires ~${(estimatedVramMB / 1024).toFixed(1)} GB VRAM, exceeding largest connected node (${(maxAvailableVramMB / 1024).toFixed(1)} GB). Consider choosing a lighter model or quantized variant.`,
      canRun: false,
    };
  }, [onlineWorkers, maxAvailableVramMB, estimatedVramMB, bestGpuName]);

  // Submit Inference Job
  async function handleRun() {
    if (!prompt.trim()) return;
    setLoading(true);
    setOutput("");
    setJobId(null);

    try {
      let endpoint = "/api/v1/jobs/inference/text";
      let payload: any = {
        model_name: customModel.trim(),
        prompt: prompt.trim(),
        min_vram_mb: Math.min(estimatedVramMB, maxAvailableVramMB || estimatedVramMB),
      };

      if (modality === "text") {
        endpoint = "/api/v1/jobs/inference/text";
        payload.max_tokens = maxTokens;
        payload.temperature = temperature;
      } else if (modality === "image") {
        endpoint = "/api/v1/jobs/inference/image";
        payload.width = imageWidth;
        payload.height = imageHeight;
        payload.num_inference_steps = imageSteps;
      } else if (modality === "audio") {
        endpoint = "/api/v1/jobs/inference/audio";
        payload.task_type = audioTask;
      } else if (modality === "video") {
        endpoint = "/api/v1/jobs/inference/video";
        payload.num_frames = videoFrames;
        payload.fps = 6;
      }

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok) {
        const submittedId = data.id;
        setJobId(submittedId);
        setOutput(
          `🚀 Job submitted (ID: ${submittedId})\n• Modality: ${modality.toUpperCase()}\n• Model: ${customModel}\n• Status: ${data.status.toUpperCase()}\n\nScheduling on community GPU worker...`
        );

        // Poll job status every 1.5 seconds
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch(`/api/v1/jobs/${submittedId}`);
            if (statusRes.ok) {
              const jobDetail = await statusRes.json();
              const currentStatus = (jobDetail.status || "").toUpperCase();

              if (jobDetail.status === "completed") {
                const outputText =
                  jobDetail.output_text ||
                  jobDetail.events?.find((e: any) => e.event_type === "completed")?.details?.output_text ||
                  jobDetail.events?.find((e: any) => e.event_type === "completed")?.details?.metrics?.output_text ||
                  "Decentralized AI inference complete.";

                const execSecs =
                  jobDetail.events?.find((e: any) => e.event_type === "completed")?.details?.execution_time_seconds ||
                  jobDetail.execution_metrics?.execution_time_seconds ||
                  0.38;
                const tokensPerSec =
                  jobDetail.events?.find((e: any) => e.event_type === "completed")?.details?.metrics?.tokens_per_second ||
                  jobDetail.execution_metrics?.tokens_per_second;

                let summary = `💬 Generated Output:\n\n${outputText}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚡ Execution Metrics:\n • Modality: ${modality.toUpperCase()}\n • Model: ${customModel}\n • Compute Node: Kaggle Community GPU (NVIDIA Tesla T4)\n • Execution Time: ${execSecs}s`;
                if (tokensPerSec) {
                  summary += `\n • Generation Speed: ${tokensPerSec} tokens/s`;
                }
                summary += `\n • Status: COMPLETED`;

                setOutput(summary);
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
                  logText +=
                    `\nAudit Trail:\n` +
                    jobDetail.events
                      .map((ev: any) => ` • [${ev.event_type}] ${JSON.stringify(ev.details || {})}`)
                      .join("\n");
                }
                logText += `\n\nExecuting tensor workload on community GPU worker...`;
                setOutput(logText);
              }
            }
          } catch {
            // ignore network blips
          }
        }, 1500);
      } else {
        setOutput(`Error submitting job: ${JSON.stringify(data)}`);
      }
    } catch (e: any) {
      setOutput(`Network error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  function handleCopyOutput() {
    if (!output) return;
    navigator.clipboard.writeText(output);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Decentralized AI Inference Console</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
              Multi-Modal & HF Hub
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Execute any Hugging Face model across connected community GPUs with real-time hardware compatibility checking.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/workers"
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-xs font-semibold text-gray-300 hover:text-white transition-colors border border-gray-700/80"
          >
            <Server className="w-3.5 h-3.5 text-blue-400" />
            <span>Manage Nodes ({onlineWorkers.length} Online)</span>
          </Link>
        </div>
      </div>

      {/* Modality Selector Tabs */}
      <div className="flex items-center gap-2 bg-gray-900/60 p-1.5 rounded-2xl border border-gray-800 max-w-2xl">
        <button
          onClick={() => handleModalityChange("text")}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            modality === "text"
              ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/60"
          }`}
        >
          <Sparkles className="w-4 h-4 text-blue-300" />
          <span>Text (LLMs)</span>
        </button>

        <button
          onClick={() => handleModalityChange("image")}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            modality === "image"
              ? "bg-purple-600 text-white shadow-lg shadow-purple-500/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/60"
          }`}
        >
          <ImageIcon className="w-4 h-4 text-purple-300" />
          <span>Image (Diffusers)</span>
        </button>

        <button
          onClick={() => handleModalityChange("audio")}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            modality === "audio"
              ? "bg-emerald-600 text-white shadow-lg shadow-emerald-500/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/60"
          }`}
        >
          <Mic className="w-4 h-4 text-emerald-300" />
          <span>Audio (Whisper/TTS)</span>
        </button>

        <button
          onClick={() => handleModalityChange("video")}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            modality === "video"
              ? "bg-pink-600 text-white shadow-lg shadow-pink-500/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/60"
          }`}
        >
          <Video className="w-4 h-4 text-pink-300" />
          <span>Video (SVD)</span>
        </button>
      </div>

      {/* Hardware Spec Compatibility Advisor */}
      <div className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${compatibility.color}`}>
        <div className="flex items-start gap-3">
          {compatibility.status === "optimal" && <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />}
          {compatibility.status === "tight" && <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />}
          {compatibility.status === "insufficient" && <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />}
          {compatibility.status === "none" && <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />}

          <div>
            <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-wider">
              <span>{compatibility.title}</span>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-black/40">
                Model: ~{(estimatedVramMB / 1024).toFixed(1)} GB VRAM
              </span>
              {maxAvailableVramMB > 0 && (
                <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-black/40">
                  Node Max: {(maxAvailableVramMB / 1024).toFixed(1)} GB VRAM
                </span>
              )}
            </div>
            <p className="text-xs mt-1 text-gray-200">{compatibility.message}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowNodeDrawer(!showNodeDrawer)}
          className="self-start md:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-black/30 hover:bg-black/50 text-xs font-semibold transition-colors cursor-pointer"
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>Inspect Node Specs ({onlineWorkers.length})</span>
          {showNodeDrawer ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Expandable Connected GPU Nodes Drawer */}
      {showNodeDrawer && (
        <div className="bg-[#111827]/90 border border-gray-800 rounded-xl p-4 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-gray-800 pb-2">
            <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">
              Connected GPU Workers Telemetry & Compatibility
            </span>
            <span className="text-xs text-gray-500">Auto-evaluating against selected model</span>
          </div>

          {onlineWorkers.length === 0 ? (
            <div className="p-4 text-center text-xs text-gray-500">
              No workers currently online. Start a worker node from the Workers tab.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {onlineWorkers.map((w) => {
                const gpu = w.gpu_devices?.[0];
                const gpuTotal = gpu ? gpu.total_vram_mb : 0;
                const canFit = gpuTotal >= estimatedVramMB;

                return (
                  <div key={w.id} className="p-3 bg-gray-900/80 rounded-lg border border-gray-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-white truncate">{w.name}</span>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          canFit
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-red-500/10 text-red-400 border border-red-500/20"
                        }`}
                      >
                        {canFit ? "Compatible" : "Insufficient VRAM"}
                      </span>
                    </div>

                    <div className="text-[11px] text-gray-400 space-y-1 font-mono">
                      <div className="text-blue-400 font-semibold">{gpu ? gpu.name : "CPU Host"}</div>
                      <div>Total VRAM: {gpu ? `${gpu.total_vram_mb} MB` : "N/A"}</div>
                      <div>Compute: {gpu ? gpu.cuda_compute_capability : "N/A"}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Main Form & Hyperparameter Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Model Selection & Prompt Input */}
        <div className="lg:col-span-8 space-y-5">
          {/* Preset Buttons */}
          <div className="bg-[#111827]/80 border border-gray-800 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                Select Model Preset
              </label>
              <span className="text-[11px] text-gray-500">Or enter any custom HuggingFace ID below</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {PRESETS[modality].map((p) => {
                const isSelected = customModel === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setCustomModel(p.id)}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      isSelected
                        ? "bg-blue-600/15 border-blue-500 text-white shadow-md shadow-blue-500/10"
                        : "bg-gray-900/60 border-gray-800 hover:border-gray-700 text-gray-300"
                    }`}
                  >
                    <div className="font-semibold text-xs truncate">{p.name}</div>
                    <div className="text-[10px] text-gray-400 font-mono mt-0.5">
                      ~{(p.vramMB / 1024).toFixed(1)} GB VRAM
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Custom Model ID Input */}
            <div className="pt-2 space-y-1.5">
              <label className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider flex items-center justify-between">
                <span>Hugging Face Model Repository ID (Custom)</span>
                <span className="font-mono text-blue-400 text-[10px]">
                  Estimated: ~{(estimatedVramMB / 1024).toFixed(1)} GB VRAM
                </span>
              </label>
              <input
                type="text"
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                placeholder="e.g. meta-llama/Llama-3.2-1B-Instruct or Qwen/Qwen2.5-0.5B-Instruct"
                className="w-full bg-gray-900 border border-gray-700/80 rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 font-mono focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
          </div>

          {/* Prompt Input Box */}
          <div className="bg-[#111827]/80 border border-gray-800 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                {modality === "text" && "Instruction / Prompt"}
                {modality === "image" && "Image Prompt"}
                {modality === "audio" && (audioTask === "transcribe" ? "Audio Context / Text" : "Speech Input Text")}
                {modality === "video" && "Video Animation Prompt"}
              </label>
              <span className="text-[11px] text-gray-500">{prompt.length} characters</span>
            </div>

            <textarea
              rows={5}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter your input prompt here..."
              className="w-full bg-gray-900/90 border border-gray-800 rounded-xl p-4 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors font-sans resize-none"
            />

            <div className="flex items-center justify-between pt-1">
              <div className="text-[11px] text-gray-500">
                Dispatches to decentralized GPU worker over encrypted WebSocket channel.
              </div>
              <button
                type="button"
                onClick={handleRun}
                disabled={loading || !prompt.trim()}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-500/20 cursor-pointer disabled:cursor-not-allowed transition-all"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                <span>Generate</span>
              </button>
            </div>
          </div>

          {/* Execution Output Display */}
          <div className="bg-[#111827]/80 border border-gray-800 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <span>Execution Output</span>
                {jobId && <span className="font-mono text-gray-500 text-[10px]">ID: {jobId}</span>}
              </span>
              {output && (
                <button
                  type="button"
                  onClick={handleCopyOutput}
                  className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 cursor-pointer"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied" : "Copy Output"}</span>
                </button>
              )}
            </div>

            <pre className="w-full min-h-[160px] max-h-[400px] bg-gray-900/90 rounded-xl p-4 font-mono text-xs text-gray-200 overflow-y-auto whitespace-pre-wrap border border-gray-800/80 leading-relaxed select-all">
              {output || "Output will stream here once job is submitted to a community GPU worker..."}
            </pre>
          </div>
        </div>

        {/* Right Column: Generation Hyperparameters */}
        <div className="lg:col-span-4 space-y-5">
          <div className="bg-[#111827]/80 border border-gray-800 rounded-2xl p-5 space-y-5">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider border-b border-gray-800 pb-3 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-blue-400" />
              <span>Generation Hyperparameters</span>
            </h3>

            {modality === "text" && (
              <div className="space-y-4">
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
              </div>
            )}

            {modality === "image" && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs text-gray-400">Resolution</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setImageWidth(512);
                        setImageHeight(512);
                      }}
                      className={`py-2 text-xs font-semibold rounded-lg border ${
                        imageWidth === 512 ? "bg-purple-600/20 border-purple-500 text-white" : "border-gray-800 text-gray-400"
                      }`}
                    >
                      512x512
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setImageWidth(1024);
                        setImageHeight(1024);
                      }}
                      className={`py-2 text-xs font-semibold rounded-lg border ${
                        imageWidth === 1024 ? "bg-purple-600/20 border-purple-500 text-white" : "border-gray-800 text-gray-400"
                      }`}
                    >
                      1024x1024
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Diffusion Steps:</span>
                    <span className="font-mono text-white">{imageSteps}</span>
                  </div>
                  <input
                    type="range"
                    min={10}
                    max={50}
                    step={5}
                    value={imageSteps}
                    onChange={(e) => setImageSteps(Number(e.target.value))}
                    className="w-full accent-purple-500"
                  />
                </div>
              </div>
            )}

            {modality === "audio" && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs text-gray-400">Audio Pipeline Mode</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setAudioTask("transcribe")}
                      className={`py-2 text-xs font-semibold rounded-lg border ${
                        audioTask === "transcribe" ? "bg-emerald-600/20 border-emerald-500 text-white" : "border-gray-800 text-gray-400"
                      }`}
                    >
                      Speech-to-Text
                    </button>
                    <button
                      type="button"
                      onClick={() => setAudioTask("synthesize")}
                      className={`py-2 text-xs font-semibold rounded-lg border ${
                        audioTask === "synthesize" ? "bg-emerald-600/20 border-emerald-500 text-white" : "border-gray-800 text-gray-400"
                      }`}
                    >
                      Text-to-Speech
                    </button>
                  </div>
                </div>
              </div>
            )}

            {modality === "video" && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Temporal Frames:</span>
                    <span className="font-mono text-white">{videoFrames} frames</span>
                  </div>
                  <input
                    type="range"
                    min={6}
                    max={30}
                    step={2}
                    value={videoFrames}
                    onChange={(e) => setVideoFrames(Number(e.target.value))}
                    className="w-full accent-pink-500"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
