"use client";

import { useState, useEffect } from "react";
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
  ShieldAlert,
  HardDrive,
  ExternalLink,
  ChevronRight,
  HelpCircle,
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
  const [currentUser, setCurrentUser] = useState<any | null>(null);

  // Live Connected Workers
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loadingWorkers, setLoadingWorkers] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

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
      }
    } catch {
      // ignore network blips
    } finally {
      setLoadingWorkers(false);
    }
  }

  useEffect(() => {
    fetchWorkers();
    const interval = setInterval(fetchWorkers, 4000);
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

  // Handle Account Registration
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
        setCurrentUser(data);
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

  // Generate Setup Code Script
  const activeWorkerId = regData?.worker_id || "YOUR_WORKER_ID";
  const activeToken = regData?.token || "YOUR_WORKER_TOKEN";
  const activeWsUrl = regData?.websocket_url || "wss://your-tunnel-url/ws/workers";

  const setupScripts: Record<string, string> = {
    kaggle: `# 🚀 Run Decentralized Worker on Kaggle GPU (Tesla T4)
!git clone https://github.com/liladhiee-web/Decentralized.git /kaggle/working/gooys || (cd /kaggle/working/gooys && git pull)
%cd /kaggle/working/gooys
!pip install -q pydantic websockets aiohttp torch transformers psutil pynvml pillow

import os
os.environ["WORKER_ID"] = "${activeWorkerId}"
os.environ["WORKER_TOKEN"] = "${activeToken}"
os.environ["COORDINATOR_WS_URL"] = "${activeWsUrl}"

!python -m worker.agent`,

    colab: `# 🚀 Run Decentralized Worker on Google Colab (Tesla T4 / A100)
!git clone https://github.com/liladhiee-web/Decentralized.git /content/gooys || (cd /content/gooys && git pull)
%cd /content/gooys
!pip install -q pydantic websockets aiohttp torch transformers psutil pynvml pillow

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
  const totalVramGB = workers.reduce(
    (acc, w) => acc + (w.gpu_devices?.reduce((gAcc, g) => gAcc + g.total_vram_mb, 0) || 0),
    0
  ) / 1024;
  const totalJobsDone = workers.reduce((acc, w) => acc + (w.total_jobs_completed || 0), 0);

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-12">
      {/* Top Banner & Platform Stats */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Compute Workers & Node Management</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Community Compute
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Register your GPU nodes, obtain worker credentials, and contribute compute from Kaggle, Colab, or local GPUs.
          </p>
        </div>

        <button
          onClick={fetchWorkers}
          className="flex items-center gap-2 self-start md:self-auto px-3.5 py-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-xs font-medium text-gray-300 hover:text-white transition-colors border border-gray-700/80 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${loadingWorkers ? "animate-spin" : ""}`} />
          <span>Refresh Nodes</span>
        </button>
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
            Ready to accept inference tasks
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
          <div className="mt-2 text-[11px] text-gray-400">
            High throughput tensor memory
          </div>
        </div>

        <div className="bg-[#111827]/80 border border-gray-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Completed Tasks</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">{totalJobsDone}</span>
            <span className="text-xs text-gray-500">jobs processed</span>
          </div>
          <div className="mt-2 text-[11px] text-gray-400">
            Across distributed worker fleet
          </div>
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
          <div className="mt-2 text-[11px] text-gray-400">
            Direct crypto / credit settlement
          </div>
        </div>
      </div>

      {/* Main Two-Column Workflow Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
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

                    {/* WORKER_ID */}
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

                    {/* WORKER_TOKEN */}
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

                    {/* WEBSOCKET_URL */}
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
                The worker connects back to the coordinator over secure WebSockets with heartbeat telemetry (GPU VRAM, temperature, compute capability). Jobs are dispatched automatically without exposing open ports or requiring port forwarding!
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Live Connected Workers Fleet Section */}
      <div className="space-y-4">
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
                        <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`}></span>
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
                            ></div>
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

