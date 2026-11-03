import { getJobs } from "@/lib/api";
import { ListFilter, Play, CheckCircle2, Clock, XCircle, AlertTriangle } from "lucide-react";

export const revalidate = 5;

export default async function JobsPage() {
  const jobs = await getJobs();

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Job Execution History</h1>
          <p className="text-sm text-gray-400 mt-1">
            Audit logs and real-time lifecycle tracking for inference dispatches and training rounds.
          </p>
        </div>
      </div>

      <div className="bg-[#111827]/80 border border-gray-800 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-400">
            <thead className="bg-[#0c121e]/80 text-xs uppercase tracking-wider text-gray-400 border-b border-gray-800">
              <tr>
                <th className="px-6 py-3.5">Job ID</th>
                <th className="px-6 py-3.5">Type</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Assigned Worker</th>
                <th className="px-6 py-3.5">Cost</th>
                <th className="px-6 py-3.5">Created</th>
                <th className="px-6 py-3.5">Completed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/40">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    No compute jobs recorded in the system yet.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-blue-400">{job.id.slice(0, 8)}</td>
                    <td className="px-6 py-4 font-medium text-white capitalize">{job.type.replace("_", " ")}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          job.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : job.status === "running" || job.status === "dispatched"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : job.status === "failed"
                            ? "bg-red-500/10 text-red-400 border border-red-500/20"
                            : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
                        }`}
                      >
                        {job.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-400">
                      {(job as any).assigned_worker_id ? (job as any).assigned_worker_id.slice(0, 8) : "Pending"}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-300">
                      {job.execution_cost_credits.toFixed(4)} cr
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-500">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-500">
                      {job.completed_at ? new Date(job.completed_at).toLocaleTimeString() : "-"}
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

