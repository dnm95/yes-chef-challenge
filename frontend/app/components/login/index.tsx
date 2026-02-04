"use client";

import { loginAction } from "@/app/actions";
import { useState } from "react";
import { FaLock, FaArrowRight, FaSpinner } from "react-icons/fa6";

export default function LoginForm() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (formData: FormData) => {
    setLoading(true);
    setError("");
    
    const result = await loginAction(formData);
    
    if (!result.success) {
      setError(result.message || "Unknown error occurred");
      setLoading(false);
    } else {
      // Force reload to refresh Server Components and read the new cookie
      window.location.reload(); 
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 font-sans">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
        
        {/* Header */}
        <div className="text-center mb-8">
          <div className="bg-indigo-100 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 text-indigo-600 shadow-sm">
            <FaLock size={24} />
          </div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Yes Chef AI</h1>
          <p className="text-slate-500 text-sm mt-2 font-medium">Restricted Access Environment</p>
        </div>

        {/* Form */}
        <form action={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              Access Password
            </label>
            <input
              type="password"
              name="password"
              placeholder="••••••••"
              required
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 outline-none transition-all text-slate-800 placeholder:text-slate-300"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 text-center font-medium animate-pulse">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 cursor-pointer bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-indigo-200 transition-all flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed hover:-translate-y-0.5 active:translate-y-0"
          >
            {loading ? (
              <>
                <FaSpinner className="animate-spin" /> Verifying...
              </>
            ) : (
              <>
                Enter Dashboard <FaArrowRight />
              </>
            )}
          </button>
        </form>
        
        <div className="mt-6 text-center">
          <p className="text-xs text-slate-400">
            Internal tool for estimation & pricing.
          </p>
        </div>
      </div>
    </div>
  );
}
