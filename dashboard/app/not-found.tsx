import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <h2 className="text-3xl font-bold text-slate-100">404 - Page Not Found</h2>
      <p className="mt-2 text-slate-400">The requested page or resource could not be found.</p>
      <Link
        href="/"
        className="mt-6 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
      >
        Return to Overview
      </Link>
    </div>
  );
}

