import Link from "next/link";
import { Cpu, Server, Zap, Activity, ArrowUpRight, Play, Flame } from "lucide-react";
import { getWorkers, getJobs } from "@/lib/api";

export const revalidate = 5;

export default async function DashboardPage() {
  const [workers, jobs] = await Promise.all([getWorkers(), getJobs()]);

  const activeWorkers = workers.filter((w) => w.status === "idle" || w.status === "busy");
  const totalGpus = activeWorkers.reduce((acc, w) => acc + (w.gpu_devices ? w.gpu_devices.length : 0), 0);
  const totalVramGb = Math.round(
    activeWorkers.reduce((acc, w) => {
      const vram = w.gpu_devices ? w.gpu_devices.reduce((sum, g) => sum + g.total_vram_mb, 0) : 0;
      return acc + vram;
    }, 0) / 1024
  );

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Title & Quick Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System Infrastructure Overview</h1>
          <p className="text-sm text-gray-400 mt-1">
            Community-powered GPU clusters running decentralized inference and parameter-efficient training.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/inference"
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-500/20"
          >
            <Play className="w-4 h-4" />
            <span>Run Inference</span>
          </Link>
          <Link
            href="/training"
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-lg text-sm font-medium transition-colors"
          >
            <Flame className="w-4 h-4 text-amber-400" />
            <span>New LoRA Job</span>
          </Link>
        </div>
      </div>

      {/* Primary KPI Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="p-6 bg-[#111827]/80 border border-gray-800/80 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Active Community GPUs</span>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{totalGpus}</span>
            <span className="text-xs text-emerald-400 font-medium">Online</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">{activeWorkers.length} nodes connected</div>
        </div>

        <div className="p-6 bg-[#111827]/80 border border-gray-800/80 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Compute Capacity</span>
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <Server className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{totalVramGb}</span>
            <span className="text-xs text-gray-400 font-medium">GB VRAM</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">High-bandwidth GPU memory</div>
        </div>

        <div className="p-6 bg-[#111827]/80 border border-gray-800/80 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Jobs Executed</span>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{jobs.length}</span>
            <span className="text-xs text-purple-400 font-medium">Total</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">Inference & LoRA rounds</div>
        </div>

        <div className="p-6 bg-[#111827]/80 border border-gray-800/80 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Coordinator Latency</span>
            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">&lt; 2</span>
            <span className="text-xs text-emerald-400 font-medium">ms</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">Postgres & Redis dispatch loop</div>
        </div>
      </div>

      {/* Live Recent Workloads Table */}
      <div className="bg-[#111827]/80 border border-gray-800/80 rounded-xl overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-gray-800/80 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Recent Workload Dispatches</h2>
          <Link href="/jobs" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
            View All <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-400">
            <thead className="bg-[#0c121e]/80 text-xs uppercase tracking-wider text-gray-400 border-b border-gray-800/60">
              <tr>
                <th className="px-6 py-3.5">Job ID</th>
                <th className="px-6 py-3.5">Workload Type</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Cost</th>
                <th className="px-6 py-3.5">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/40">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    No compute jobs executed yet. Launch text inference or a LoRA training run.
                  </td>
                </tr>
              ) : (
                jobs.slice(0, 5).map((j) => (
                  <tr key={j.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-gray-300">{j.id.slice(0, 8)}</td>
                    <td className="px-6 py-4 font-medium text-white capitalize">{j.type.replace("_", " ")}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          j.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : j.status === "running" || j.status === "dispatched"
                            ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                            : j.status === "failed"
                            ? "bg-red-500/10 text-red-400 border border-red-500/20"
                            : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
                        }`}
                      >
                        {j.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-300">
                      {j.execution_cost_credits.toFixed(4)} credits
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-500">
                      {new Date(j.created_at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

