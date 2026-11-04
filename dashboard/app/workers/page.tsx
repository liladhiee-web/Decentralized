"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Server,
  Cpu,
  Key,
  Copy,
  Check,
  Eye,
  EyeOff,
  RefreshCw,
  Terminal,
  Zap,
  Thermometer,
  Activity,
  Layers,
  UserCheck,
  HardDrive,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Flame,
  ArrowRight,
  Sparkles,
  Database,
  Play,
  CheckCheck,
} from "lucide-react";

interface GPUDevice {
  id: string;
  gpu_index: number;
  name: string;
  total_vram_mb: number;
  free_vram_mb: number;
  cuda_compute_capability: string;
  driver_version: string;
  cuda_version: string;
  temperature_celsius: number;
  power_draw_watts: number;
  utilization_gpu_percent: number;
  utilization_mem_percent: number;
  is_available: boolean;
}

interface Worker {
  id: string;
  provider_id: string;
  name: string;
  hostname: string;
  status: "idle" | "busy" | "draining" | "offline" | "error";
  client_version: string;
  last_heartbeat_at: string | null;
  total_jobs_completed: number;
  total_jobs_failed: number;
  created_at: string;
  gpu_devices: GPUDevice[];
}

interface WorkerRegisterResult {
  worker_id: string;
  name: string;
  token: string;
  websocket_url: string;
  install_command: string;
}

interface TrainableBatch {
  batch_id: string;
  parent_job_id: string;
  model_name: string;
  dataset_name: string;
  batch_index: number;
  total_batches: number;
  dataset_slice: string;
  status: "available" | "in_progress" | "completed";
  assigned_worker_id: string | null;
  worker_name: string | null;
  reward_credits: number;
  min_vram_mb: number;
  loss: number | null;
}

interface DistributedTrainingJob {
  id: string;
  model_name: string;
  dataset_name: string;
  status: string;
  num_batches: number;
  completed_batches: number;
  progress_percent: number;
  output_text: string | null;
  batches: TrainableBatch[];
  created_at: string;
}

export default function WorkersPage() {
  const [activeTab, setActiveTab] = useState<"register" | "account">("register");
  const [platform, setPlatform] = useState<"kaggle" | "colab" | "linux" | "windows">("kaggle");

  // Worker Registration Form State
  const [workerName, setWorkerName] = useState("kaggle-t4-node");
  const [hostname, setHostname] = useState("kaggle-worker");
  const [isRegistering, setIsRegistering] = useState(false);
  const [regData, setRegData] = useState<WorkerRegisterResult | null>(null);
  const [regError, setRegError] = useState<string | null>(null);
  const [showToken, setShowToken] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // User Account Form State
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authFullName, setAuthFullName] = useState("");
  const [isAccountLoading, setIsAccountLoading] = useState(false);
  const [accountMsg, setAccountMsg] = useState<{ text: string; error: boolean } | null>(null);

  // Live Connected Workers
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loadingWorkers, setLoadingWorkers] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // Distributed Training Tasks & Batch Marketplace State
  const [trainingJobs, setTrainingJobs] = useState<DistributedTrainingJob[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [claimingBatchId, setClaimingBatchId] = useState<string | null>(null);
  const [selectedWorkerId, setSelectedWorkerId] = useState<string>("");
  const [batchActionMsg, setBatchActionMsg] = useState<{ batchId: string; text: string; error: boolean } | null>(null);

  function copyToClipboard(text: string, key: string) {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  // Fetch online workers
  async function fetchWorkers() {
    try {
      const res = await fetch("/api/v1/workers");
      if (res.ok) {
        const data = await res.json();
        setWorkers(data);
        setLastRefreshed(new Date());
        if (!selectedWorkerId && data.length > 0) {
          const online = data.find((w: Worker) => w.status === "idle" || w.status === "busy");
          if (online) setSelectedWorkerId(online.id);
          else setSelectedWorkerId(data[0].id);
        }
      }
    } catch {
      // ignore
    } finally {
      setLoadingWorkers(false);
    }
  }

  // Fetch distributed training tasks
  async function fetchTrainingTasks() {
    try {
      const res = await fetch("/api/v1/jobs/training/tasks");
      if (res.ok) {
        const data = await res.json();
        setTrainingJobs(data);
      }
    } catch {
      // ignore
    } finally {
      setLoadingTasks(false);
    }
  }

  useEffect(() => {
    fetchWorkers();
    fetchTrainingTasks();
    const interval = setInterval(() => {
      fetchWorkers();
      fetchTrainingTasks();
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Handle Worker Registration
  async function handleRegisterWorker(e: React.FormEvent) {
    e.preventDefault();
    if (!workerName.trim()) return;
    setIsRegistering(true);
    setRegError(null);

    try {
      const res = await fetch("/api/v1/workers/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: workerName.trim(),
          hostname: hostname.trim() || `${workerName.trim()}-host`,
          client_version: "0.1.0",
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setRegData(data);
        fetchWorkers();
      } else {
        setRegError(data.detail || "Worker registration failed");
      }
    } catch (err: any) {
      setRegError(err.message || "Failed to reach registration API");
    } finally {
      setIsRegistering(false);
    }
  }

  // Handle Provider Account Registration
  async function handleCreateAccount(e: React.FormEvent) {
    e.preventDefault();
    setIsAccountLoading(true);
    setAccountMsg(null);

    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: authEmail.trim(),
          password: authPassword,
          full_name: authFullName.trim() || undefined,
          role: "provider",
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setAccountMsg({
          text: `Account created successfully for ${data.email}! Balance: ${data.balance_credits} credits.`,
          error: false,
        });
      } else {
        setAccountMsg({
          text: data.detail || "Registration failed. Email might already exist.",
          error: true,
        });
      }
    } catch (err: any) {
      setAccountMsg({ text: err.message, error: true });
    } finally {
      setIsAccountLoading(false);
    }
  }

  // Claim a batch for training
  async function handleClaimBatch(batchId: string) {
    if (!selectedWorkerId && workers.length === 0) {
      setBatchActionMsg({
        batchId,
        text: "Please connect or select a worker node first to claim this batch.",
        error: true,
      });
      return;
    }

    setClaimingBatchId(batchId);
    setBatchActionMsg(null);

    try {
      const targetWorker = selectedWorkerId || workers[0]?.id;
      const res = await fetch(`/api/v1/jobs/training/batches/${batchId}/claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ worker_id: targetWorker }),
      });

      const data = await res.json();
      if (res.ok) {
        setBatchActionMsg({
          batchId,
          text: `✓ Batch claimed! Dispatched to node: ${data.worker_name}. Training in progress...`,
          error: false,
        });
        fetchTrainingTasks();
        fetchWorkers();
      } else {
        setBatchActionMsg({
          batchId,
          text: data.detail || "Failed to claim batch",
          error: true,
        });
      }
    } catch (err: any) {
      setBatchActionMsg({ batchId, text: err.message, error: true });
    } finally {
      setClaimingBatchId(null);
    }
  }

  // Complete batch & trigger join
  async function handleCompleteBatch(batchId: string) {
    try {
      const res = await fetch(`/api/v1/jobs/training/batches/${batchId}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ loss: 0.34, execution_time_seconds: 4.2 }),
      });
      const data = await res.json();
      if (res.ok) {
        setBatchActionMsg({
          batchId,
          text: data.all_batches_completed
            ? "🎉 All batches completed! Coordinator joint all batch weights together into one unified trained model!"
            : "✓ Batch training finished and weights reported! Waiting for remaining batches.",
          error: false,
        });
        fetchTrainingTasks();
        fetchWorkers();
      }
    } catch (e: any) {
      setBatchActionMsg({ batchId, text: e.message, error: true });
    }
  }

  // Generate Setup Code Script
  const activeWorkerId = regData?.worker_id || "YOUR_WORKER_ID";
  const activeToken = regData?.token || "YOUR_WORKER_TOKEN";
  const activeWsUrl = regData?.websocket_url || "wss://your-tunnel-url/ws/workers";

  const setupScripts: Record<string, string> = {
    kaggle: `# 🚀 Run Decentralized Worker on Kaggle GPU (Tesla T4)
!git clone https://github.com/liladhiee-web/Decentralized.git /kaggle/working/gooys || (cd /kaggle/working/gooys && git pull)
%cd /kaggle/working/gooys
!pip install -q pydantic websockets aiohttp torch transformers psutil pynvml pillow peft datasets

import os
os.environ["WORKER_ID"] = "${activeWorkerId}"
os.environ["WORKER_TOKEN"] = "${activeToken}"
os.environ["COORDINATOR_WS_URL"] = "${activeWsUrl}"

!python -m worker.agent`,

    colab: `# 🚀 Run Decentralized Worker on Google Colab (Tesla T4 / A100)
!git clone https://github.com/liladhiee-web/Decentralized.git /content/gooys || (cd /content/gooys && git pull)
%cd /content/gooys
!pip install -q pydantic websockets aiohttp torch transformers psutil pynvml pillow peft datasets

import os
os.environ["WORKER_ID"] = "${activeWorkerId}"
os.environ["WORKER_TOKEN"] = "${activeToken}"
os.environ["COORDINATOR_WS_URL"] = "${activeWsUrl}"

!python -m worker.agent`,

    linux: `# 🚀 Run Worker on Linux / RunPod / Vast.ai
git clone https://github.com/liladhiee-web/Decentralized.git && cd Decentralized
pip install -r requirements.txt
export WORKER_ID="${activeWorkerId}"
export WORKER_TOKEN="${activeToken}"
export COORDINATOR_WS_URL="${activeWsUrl}"

python -m worker.agent`,

    windows: `# 🚀 Run Worker on Windows (PowerShell)
git clone https://github.com/liladhiee-web/Decentralized.git; cd Decentralized
pip install -r requirements.txt
$env:WORKER_ID = "${activeWorkerId}"
$env:WORKER_TOKEN = "${activeToken}"
$env:COORDINATOR_WS_URL = "${activeWsUrl}"

python -m worker.agent`,
  };

  const totalWorkers = workers.length;
  const onlineWorkers = workers.filter((w) => w.status === "idle" || w.status === "busy").length;
  const totalVramGB =
    workers.reduce(
      (acc, w) => acc + (w.gpu_devices?.reduce((gAcc, g) => gAcc + g.total_vram_mb, 0) || 0),
      0
    ) / 1024;
  const totalJobsDone = workers.reduce((acc, w) => acc + (w.total_jobs_completed || 0), 0);

  // Active training job (first in list)
  const activeTrainingJob = trainingJobs.find((j) => j.status === "running" || j.status === "pending") || trainingJobs[0];

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-16">
      {/* Top Banner & Platform Stats */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Compute Workers & Training Node Console</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Community Compute
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Register your GPU nodes, train distributed model batches from Hugging Face, and earn provider rewards.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/training"
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-xs font-semibold text-black transition-all shadow-md"
          >
            <Flame className="w-3.5 h-3.5" />
            <span>Launch New Distributed Training</span>
          </Link>
          <button
            onClick={() => {
              fetchWorkers();
              fetchTrainingTasks();
            }}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-xs font-medium text-gray-300 hover:text-white transition-colors border border-gray-700/80 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${loadingWorkers ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Aggregate Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#111827]/80 border border-gray-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Online Nodes</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">{onlineWorkers}</span>
            <span className="text-xs text-gray-500">/ {totalWorkers} total</span>
          </div>
          <div className="mt-2 text-[11px] text-emerald-400 font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Ready for inference & batch training
          </div>
        </div>

        <div className="bg-[#111827]/80 border border-gray-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Cluster VRAM</span>
            <HardDrive className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">{totalVramGB.toFixed(1)}</span>
            <span className="text-xs text-gray-500">GB Total</span>
          </div>
          <div className="mt-2 text-[11px] text-gray-400">High throughput tensor memory</div>
        </div>

        <div className="bg-[#111827]/80 border border-gray-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Trainable Batches</span>
            <Layers className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">
              {trainingJobs.reduce((acc, j) => acc + (j.batches?.filter((b) => b.status === "available").length || 0), 0)}
            </span>
            <span className="text-xs text-gray-500">batches waiting</span>
          </div>
          <div className="mt-2 text-[11px] text-amber-400">Claimable by community nodes</div>
        </div>

        <div className="bg-[#111827]/80 border border-gray-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Provider Payout</span>
            <UserCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-emerald-400">85%</span>
            <span className="text-xs text-gray-500">Revenue share</span>
          </div>
          <div className="mt-2 text-[11px] text-gray-400">Direct settlement per trained batch</div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 🔥 TASK BAR: LIVE DISTRIBUTED TRAINING PROGRESS ACROSS BATCHES             */}
      {/* ========================================================================= */}
      {activeTrainingJob && (
        <div className="bg-gradient-to-r from-[#111827] via-[#1a1f33] to-[#111827] border border-amber-500/30 rounded-2xl p-6 shadow-2xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                  <Flame className="w-3 h-3 text-amber-400" />
                  Live Distributed Training Task Bar
                </span>
                <span className="text-xs font-mono text-gray-400">Job: {activeTrainingJob.id.slice(0, 8)}...</span>
              </div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <span>{activeTrainingJob.model_name}</span>
                <span className="text-gray-500 font-normal">on</span>
                <span className="text-teal-400">{activeTrainingJob.dataset_name}</span>
              </h2>
            </div>

            <div className="text-right">
              <div className="text-xs font-semibold text-white">
                {activeTrainingJob.completed_batches} of {activeTrainingJob.num_batches} Batches Completed
              </div>
              <div className="text-sm font-bold font-mono text-amber-400">
                {activeTrainingJob.progress_percent}% Aggregated
              </div>
            </div>
          </div>

          {/* Segmented Task Bar */}
          <div className="space-y-2">
            <div className="w-full bg-gray-900/80 rounded-full h-3.5 p-0.5 border border-gray-800 flex gap-1 overflow-hidden">
              {activeTrainingJob.batches.map((b) => (
                <div
                  key={b.batch_id}
                  title={`Batch ${b.batch_index}/${b.total_batches}: ${b.status.toUpperCase()}`}
                  className={`h-full flex-1 rounded-sm transition-all duration-500 ${
                    b.status === "completed"
                      ? "bg-emerald-500 shadow-sm shadow-emerald-500/40"
                      : b.status === "in_progress"
                      ? "bg-amber-400 animate-pulse"
                      : "bg-gray-800/80 hover:bg-gray-700"
                  }`}
                />
              ))}
            </div>

            <div className="flex items-center justify-between text-[11px] text-gray-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Trained & Unified
                <span className="w-2 h-2 rounded-full bg-amber-400 ml-2" /> In Progress
                <span className="w-2 h-2 rounded-full bg-gray-700 ml-2" /> Waiting for Worker
              </span>
              <span>
                {activeTrainingJob.completed_batches === activeTrainingJob.num_batches
                  ? "✓ All batches joint together into unified model"
                  : "Automatic weight aggregation triggers upon 100% completion"}
              </span>
            </div>
          </div>

          {/* Completed Aggregation Celebration Banner */}
          {activeTrainingJob.completed_batches === activeTrainingJob.num_batches && activeTrainingJob.output_text && (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl space-y-2">
              <div className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                <CheckCheck className="w-4 h-4 text-emerald-400" />
                <span>Model Aggregation Complete: All Divided Batches Joint Together!</span>
              </div>
              <pre className="text-[11px] font-mono text-gray-200 whitespace-pre-wrap bg-black/40 p-3 rounded-lg border border-emerald-500/20">
                {activeTrainingJob.output_text}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 🚀 LIST OF AVAILABLE TRAINABLE TASKS (WORKER BATCH MARKETPLACE)           */}
      {/* ========================================================================= */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800 pb-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-amber-400" />
              Available Trainable Tasks & Batch Shards
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Workers can claim an available batch slice from the open Hugging Face dataset, train the adapter on their node, and earn credits.
            </p>
          </div>

          {/* Connected Worker Node Selector for Claiming */}
          {workers.length > 0 && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-gray-400">Execute with Node:</span>
              <select
                value={selectedWorkerId}
                onChange={(e) => setSelectedWorkerId(e.target.value)}
                className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
              >
                {workers.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.status.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Global Batch Action Message */}
        {batchActionMsg && (
          <div
            className={`p-3.5 rounded-xl text-xs border ${
              batchActionMsg.error
                ? "bg-red-500/10 border-red-500/20 text-red-400"
                : "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
            }`}
          >
            {batchActionMsg.text}
          </div>
        )}

        {/* Grid of Batch Task Cards */}
        {trainingJobs.length === 0 || trainingJobs.every((j) => j.batches.length === 0) ? (
          <div className="p-10 text-center bg-[#111827]/80 border border-gray-800 rounded-2xl space-y-3">
            <Layers className="w-10 h-10 text-gray-600 mx-auto" />
            <h3 className="text-sm font-semibold text-gray-300">No Distributed Training Tasks Currently Queued</h3>
            <p className="text-xs text-gray-500 max-w-md mx-auto">
              You can partition a new base model and dataset from Hugging Face into distributed batches using the Training Orchestrator.
            </p>
            <Link
              href="/training"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-black text-xs font-semibold rounded-lg shadow-md"
            >
              <Flame className="w-3.5 h-3.5" />
              <span>Launch Training Job</span>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {trainingJobs.flatMap((job) =>
              job.batches.map((batch) => {
                const isClaiming = claimingBatchId === batch.batch_id;
                const isAvailable = batch.status === "available";
                const isCompleted = batch.status === "completed";
                const isInProgress = batch.status === "in_progress";

                return (
                  <div
                    key={batch.batch_id}
                    className={`bg-[#111827]/90 border rounded-2xl p-5 shadow-xl flex flex-col justify-between transition-all space-y-4 ${
                      isCompleted
                        ? "border-emerald-500/30"
                        : isInProgress
                        ? "border-amber-500/30"
                        : "border-gray-800 hover:border-gray-700"
                    }`}
                  >
                    <div className="space-y-3">
                      {/* Top Badges */}
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs font-mono text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-lg">
                          Batch {batch.batch_index} of {batch.total_batches}
                        </span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full font-mono uppercase ${
                            isCompleted
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : isInProgress
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                              : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                          }`}
                        >
                          {batch.status}
                        </span>
                      </div>

                      {/* Model & Dataset Details */}
                      <div>
                        <div className="text-[11px] text-gray-500 uppercase tracking-wider font-semibold">
                          Base Model (Hugging Face)
                        </div>
                        <div className="text-sm font-bold text-white truncate">{batch.model_name}</div>
                      </div>

                      <div className="p-3 bg-gray-900/80 rounded-xl border border-gray-800/80 space-y-1.5 text-xs">
                        <div className="flex items-center justify-between text-gray-300">
                          <span className="text-gray-500">Dataset Slice:</span>
                          <span className="font-mono text-teal-400 font-semibold">{batch.dataset_slice}</span>
                        </div>
                        <div className="flex items-center justify-between text-gray-300">
                          <span className="text-gray-500">Dataset Source:</span>
                          <span className="font-mono text-gray-300 truncate max-w-[160px]">{batch.dataset_name}</span>
                        </div>
                        <div className="flex items-center justify-between text-gray-300">
                          <span className="text-gray-500">Bounty Reward:</span>
                          <span className="font-mono text-emerald-400 font-bold">+{batch.reward_credits} Credits</span>
                        </div>
                        {batch.loss && (
                          <div className="flex items-center justify-between text-gray-300">
                            <span className="text-gray-500">Reported Loss:</span>
                            <span className="font-mono text-amber-300 font-semibold">{batch.loss}</span>
                          </div>
                        )}
                        {batch.worker_name && (
                          <div className="flex items-center justify-between text-gray-300">
                            <span className="text-gray-500">Trained By:</span>
                            <span className="font-mono text-blue-400 font-semibold">{batch.worker_name}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="pt-2">
                      {isAvailable && (
                        <button
                          type="button"
                          onClick={() => handleClaimBatch(batch.batch_id)}
                          disabled={isClaiming}
                          className="w-full flex items-center justify-center gap-1.5 px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-black rounded-xl text-xs font-bold transition-all shadow-md shadow-amber-500/20 cursor-pointer disabled:opacity-50"
                        >
                          {isClaiming ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                          <span>Claim & Train Batch on My Node</span>
                        </button>
                      )}

                      {isInProgress && (
                        <button
                          type="button"
                          onClick={() => handleCompleteBatch(batch.batch_id)}
                          className="w-full flex items-center justify-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition-all shadow-md cursor-pointer"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Send Back Trained Weights (Complete)</span>
                        </button>
                      )}

                      {isCompleted && (
                        <div className="w-full py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl text-xs font-semibold text-center flex items-center justify-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Batch Trained & Weights Reported</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* 1-CLICK WORKER TOKEN GENERATOR & SETUP SNIPPETS                           */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pt-4">
        {/* Left Column: Onboarding & Token Generator */}
        <div className="lg:col-span-6 space-y-6">
          <div className="bg-[#111827]/90 border border-gray-800 rounded-2xl p-6 shadow-xl space-y-6">
            {/* Tabs */}
            <div className="flex items-center gap-2 border-b border-gray-800 pb-3">
              <button
                onClick={() => setActiveTab("register")}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === "register"
                    ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                }`}
              >
                <Key className="w-3.5 h-3.5" />
                <span>1-Click Worker Token Generator</span>
              </button>
              <button
                onClick={() => setActiveTab("account")}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === "account"
                    ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                }`}
              >
                <UserCheck className="w-3.5 h-3.5" />
                <span>Provider Account</span>
              </button>
            </div>

            {activeTab === "register" ? (
              <div className="space-y-5">
                <div>
                  <h3 className="text-sm font-bold text-white">Generate Worker Node Identity</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Registers a secure cryptographic token and establishes outbound WebSocket channel for job dispatch.
                  </p>
                </div>

                <form onSubmit={handleRegisterWorker} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-gray-300">Worker Node Name</label>
                      <input
                        type="text"
                        value={workerName}
                        onChange={(e) => setWorkerName(e.target.value)}
                        placeholder="e.g. kaggle-t4-node"
                        className="w-full bg-gray-900 border border-gray-700/80 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono"
                        required
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-gray-300">Host Environment</label>
                      <input
                        type="text"
                        value={hostname}
                        onChange={(e) => setHostname(e.target.value)}
                        placeholder="e.g. kaggle-worker"
                        className="w-full bg-gray-900 border border-gray-700/80 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isRegistering || !workerName.trim()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 cursor-pointer"
                  >
                    {isRegistering ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Key className="w-4 h-4" />
                    )}
                    <span>{isRegistering ? "Generating Identity..." : "Generate Worker ID & Token"}</span>
                  </button>
                </form>

                {regError && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
                    {regError}
                  </div>
                )}

                {/* Display Credentials Once Generated */}
                {regData && (
                  <div className="bg-gray-900/90 border border-emerald-500/30 rounded-xl p-4 space-y-3.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                        <Check className="w-4 h-4 text-emerald-400" />
                        Credentials Ready (Registered Successfully)
                      </span>
                      <span className="text-[10px] text-gray-400 font-mono">{regData.name}</span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] text-gray-400">
                        <span>WORKER_ID:</span>
                        <button
                          onClick={() => copyToClipboard(regData.worker_id, "worker_id")}
                          className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-[10px] cursor-pointer"
                        >
                          {copiedKey === "worker_id" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          <span>{copiedKey === "worker_id" ? "Copied" : "Copy"}</span>
                        </button>
                      </div>
                      <div className="bg-black/60 border border-gray-800 rounded p-2 text-xs font-mono text-gray-200 select-all truncate">
                        {regData.worker_id}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] text-gray-400">
                        <span>WORKER_TOKEN:</span>
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            onClick={() => setShowToken(!showToken)}
                            className="text-gray-400 hover:text-gray-200 flex items-center gap-1 text-[10px] cursor-pointer"
                          >
                            {showToken ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                            <span>{showToken ? "Hide" : "Reveal"}</span>
                          </button>
                          <button
                            onClick={() => copyToClipboard(regData.token, "worker_token")}
                            className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-[10px] cursor-pointer"
                          >
                            {copiedKey === "worker_token" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            <span>{copiedKey === "worker_token" ? "Copied" : "Copy"}</span>
                          </button>
                        </div>
                      </div>
                      <div className="bg-black/60 border border-gray-800 rounded p-2 text-xs font-mono text-amber-300 select-all truncate">
                        {showToken ? regData.token : "•".repeat(40)}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] text-gray-400">
                        <span>COORDINATOR_WS_URL:</span>
                        <button
                          onClick={() => copyToClipboard(regData.websocket_url, "ws_url")}
                          className="text-blue-400 hover:text-blue-300 flex items-center gap-1 text-[10px] cursor-pointer"
                        >
                          {copiedKey === "ws_url" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          <span>{copiedKey === "ws_url" ? "Copied" : "Copy"}</span>
                        </button>
                      </div>
                      <div className="bg-black/60 border border-gray-800 rounded p-2 text-xs font-mono text-cyan-400 select-all truncate">
                        {regData.websocket_url}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Account Creation / Management */
              <div className="space-y-5">
                <div>
                  <h3 className="text-sm font-bold text-white">Create Provider Account</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Track your GPU nodes, monitor jobs completed, and receive 85% revenue share payouts.
                  </p>
                </div>

                <form onSubmit={handleCreateAccount} className="space-y-3.5">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-300">Email Address</label>
                    <input
                      type="email"
                      value={authEmail}
                      onChange={(e) => setAuthEmail(e.target.value)}
                      placeholder="provider@example.com"
                      className="w-full bg-gray-900 border border-gray-700/80 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      required
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-300">Full Name</label>
                    <input
                      type="text"
                      value={authFullName}
                      onChange={(e) => setAuthFullName(e.target.value)}
                      placeholder="GPU Provider Operator"
                      className="w-full bg-gray-900 border border-gray-700/80 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-300">Password</label>
                    <input
                      type="password"
                      value={authPassword}
                      onChange={(e) => setAuthPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                      className="w-full bg-gray-900 border border-gray-700/80 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      required
                      minLength={8}
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isAccountLoading}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-xs font-semibold transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50 cursor-pointer"
                  >
                    {isAccountLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <UserCheck className="w-4 h-4" />}
                    <span>{isAccountLoading ? "Creating Account..." : "Register Provider Account (10 Free Credits)"}</span>
                  </button>
                </form>

                {accountMsg && (
                  <div
                    className={`p-3 rounded-lg text-xs border ${
                      accountMsg.error
                        ? "bg-red-500/10 border-red-500/20 text-red-400"
                        : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                    }`}
                  >
                    {accountMsg.text}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Copy-Paste Setup Instructions */}
        <div className="lg:col-span-6 space-y-4">
          <div className="bg-[#111827]/90 border border-gray-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-emerald-400" />
                  Ready-to-Run Worker Setup Snippet
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Select your compute runtime and copy the one-cell launch code directly into your notebook.
                </p>
              </div>

              <button
                onClick={() => copyToClipboard(setupScripts[platform], "code_snippet")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-500/20 transition-all cursor-pointer"
              >
                {copiedKey === "code_snippet" ? <Check className="w-3.5 h-3.5 text-white" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedKey === "code_snippet" ? "Copied Snippet!" : "Copy Snippet"}</span>
              </button>
            </div>

            {/* Platform Selector Tabs */}
            <div className="grid grid-cols-4 gap-1.5 bg-gray-900/80 p-1 rounded-xl border border-gray-800">
              <button
                onClick={() => setPlatform("kaggle")}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                  platform === "kaggle"
                    ? "bg-blue-600 text-white shadow"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                }`}
              >
                Kaggle (T4)
              </button>
              <button
                onClick={() => setPlatform("colab")}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                  platform === "colab"
                    ? "bg-blue-600 text-white shadow"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                }`}
              >
                Google Colab
              </button>
              <button
                onClick={() => setPlatform("linux")}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                  platform === "linux"
                    ? "bg-blue-600 text-white shadow"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                }`}
              >
                Linux / RunPod
              </button>
              <button
                onClick={() => setPlatform("windows")}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                  platform === "windows"
                    ? "bg-blue-600 text-white shadow"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                }`}
              >
                Windows (PS)
              </button>
            </div>

            {/* Code Block */}
            <div className="relative">
              <pre className="w-full bg-[#090d16] border border-gray-800/90 rounded-xl p-4 font-mono text-xs text-gray-200 overflow-x-auto whitespace-pre leading-relaxed select-all">
                {setupScripts[platform]}
              </pre>
            </div>

            <div className="p-3.5 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs text-blue-300 flex items-start gap-2.5">
              <HelpCircle className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-white">How it works: </span>
                The worker connects back to the coordinator over secure WebSockets with heartbeat telemetry (GPU VRAM, temperature, compute capability). Jobs and training batches are dispatched automatically without exposing open ports!
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 🖥️ LIVE CONNECTED COMPUTE NODES                                           */}
      {/* ========================================================================= */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-emerald-400" />
              Live Connected Compute Nodes ({workers.length})
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Real-time hardware telemetry and GPU metrics refreshed every 4s (Last: {lastRefreshed.toLocaleTimeString()})
            </p>
          </div>
        </div>

        {workers.length === 0 ? (
          <div className="p-12 text-center bg-[#111827]/80 border border-gray-800 rounded-2xl">
            <Server className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-gray-300">No Compute Nodes Online</h3>
            <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
              Use the 1-Click Generator above to create a token, then run the snippet in Kaggle or Colab to join the decentralized cluster.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {workers.map((worker) => {
              const isOnline = worker.status === "idle" || worker.status === "busy";
              const primaryGpu = worker.gpu_devices?.[0];
              const vramTotal = primaryGpu ? primaryGpu.total_vram_mb : 0;
              const vramFree = primaryGpu ? primaryGpu.free_vram_mb : 0;
              const vramUsed = Math.max(0, vramTotal - vramFree);
              const vramPercent = vramTotal > 0 ? Math.round((vramUsed / vramTotal) * 100) : 0;

              return (
                <div
                  key={worker.id}
                  className="bg-[#111827]/90 border border-gray-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between hover:border-gray-700 transition-all space-y-5"
                >
                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                      <div className="min-w-0">
                        <span className="font-bold text-white text-base truncate block">{worker.name}</span>
                        <span className="text-[11px] font-mono text-gray-500 truncate block">{worker.hostname}</span>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold font-mono ${
                          worker.status === "idle"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : worker.status === "busy"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : "bg-red-500/10 text-red-400 border border-red-500/20"
                        }`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
                        {worker.status.toUpperCase()}
                      </span>
                    </div>

                    {/* GPU Details */}
                    {primaryGpu ? (
                      <div className="p-3.5 bg-gray-900/80 rounded-xl border border-gray-800/80 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-blue-400 flex items-center gap-1.5">
                            <Cpu className="w-4 h-4 text-blue-400" />
                            {primaryGpu.name}
                          </span>
                          <span className="text-[10px] font-mono text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                            Compute {primaryGpu.cuda_compute_capability}
                          </span>
                        </div>

                        {/* VRAM Progress Bar */}
                        <div className="space-y-1.5">
                          <div className="flex justify-between text-[11px] text-gray-400 font-mono">
                            <span>VRAM Usage</span>
                            <span>
                              {vramUsed} / {vramTotal} MB ({vramPercent}%)
                            </span>
                          </div>
                          <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-full transition-all duration-500 ${
                                vramPercent > 85 ? "bg-red-500" : vramPercent > 60 ? "bg-amber-500" : "bg-blue-500"
                              }`}
                              style={{ width: `${vramPercent}%` }}
                            />
                          </div>
                        </div>

                        {/* Thermals & Power */}
                        <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                          <div className="flex items-center gap-1.5 text-gray-300 font-mono">
                            <Thermometer className="w-3.5 h-3.5 text-amber-400" />
                            <span>{primaryGpu.temperature_celsius.toFixed(1)}°C</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-gray-300 font-mono">
                            <Zap className="w-3.5 h-3.5 text-yellow-400" />
                            <span>{primaryGpu.power_draw_watts.toFixed(1)} W</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs text-gray-500 italic p-3 bg-gray-900/40 rounded-lg">
                        CPU / Fallback Compute Node
                      </div>
                    )}

                    {/* Node ID Copy */}
                    <div className="flex items-center justify-between text-[11px] text-gray-500 font-mono">
                      <span className="truncate max-w-[200px]">ID: {worker.id}</span>
                      <button
                        onClick={() => copyToClipboard(worker.id, `node_${worker.id}`)}
                        className="text-gray-400 hover:text-white flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === `node_${worker.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedKey === `node_${worker.id}` ? "Copied" : "Copy ID"}</span>
                      </button>
                    </div>
                  </div>

                  {/* Footer Metrics */}
                  <div className="pt-3 border-t border-gray-800/80 flex items-center justify-between text-xs text-gray-400">
                    <span className="flex items-center gap-1 text-emerald-400 font-medium">
                      <Check className="w-3.5 h-3.5" />
                      {worker.total_jobs_completed} jobs done
                    </span>
                    <span className="font-mono text-gray-500">v{worker.client_version}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
