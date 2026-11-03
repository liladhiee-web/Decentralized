import { getWorkers } from "@/lib/api";
import { Server, Cpu, Thermometer, Zap, CheckCircle2, AlertCircle } from "lucide-react";

export const revalidate = 5;

export default async function MarketplacePage() {
  const workers = await getWorkers();

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Community GPU Compute Marketplace</h1>
        <p className="text-sm text-gray-400 mt-1">
          Third-party compute provider nodes registered with outbound TLS control channels.
        </p>
      </div>

      {workers.length === 0 ? (
        <div className="p-12 text-center bg-[#111827]/80 border border-gray-800 rounded-xl">
          <Server className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-gray-300">No Workers Connected Yet</h3>
          <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
            To register a compute node, generate an install token using the CLI and run the daemon script on your GPU host.
          </p>
          <div className="mt-4 inline-block font-mono text-xs bg-gray-900 px-4 py-2 rounded-lg text-emerald-400 border border-gray-800">
            cloudai workers list
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {workers.map((worker) => {
            const isOnline = worker.status === "idle" || worker.status === "busy";
            return (
              <div
                key={worker.id}
                className="bg-[#111827]/80 border border-gray-800 rounded-xl p-6 shadow-xl flex flex-col justify-between hover:border-gray-700 transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-base truncate">{worker.name}</span>
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        worker.status === "idle"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : worker.status === "busy"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? "bg-emerald-400" : "bg-red-400"}`}></span>
                      {worker.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 font-mono mt-0.5">{worker.hostname}</div>

                  {/* GPU Devices List */}
                  <div className="mt-6 space-y-3">
                    {worker.gpu_devices && worker.gpu_devices.length > 0 ? (
                      worker.gpu_devices.map((gpu) => (
                        <div key={gpu.id} className="p-3 bg-gray-900/60 rounded-lg border border-gray-800/80">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-blue-400 flex items-center gap-1.5">
                              <Cpu className="w-3.5 h-3.5" />
                              {gpu.name}
                            </span>
                            <span className="text-[10px] font-mono text-gray-400">Compute {gpu.cuda_compute_capability}</span>
                          </div>

                          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-400">
                            <div>
                              <span className="block text-[10px] text-gray-500 uppercase">VRAM (Free/Total)</span>
                              <span className="font-mono text-gray-200">
                                {gpu.free_vram_mb} / {gpu.total_vram_mb} MB
                              </span>
                            </div>
                            <div>
                              <span className="block text-[10px] text-gray-500 uppercase">Temperature</span>
                              <span className="font-mono text-gray-200 flex items-center gap-1">
                                <Thermometer className="w-3 h-3 text-amber-400" />
                                {gpu.temperature_celsius.toFixed(1)}°C
                              </span>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-gray-500 italic">No discrete GPUs reported.</div>
                    )}
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    {worker.total_jobs_completed} completed
                  </span>
                  <span className="font-mono text-gray-500">v{worker.client_version}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

