"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import {
  FaKitchenSet, 
  FaPlay, 
  FaRotate, 
  FaCheck, 
  FaTriangleExclamation, 
  FaMicrochip, 
  FaCode,
  FaMessage,
  FaListCheck
} from "react-icons/fa6";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

// --- TYPE DEFINITIONS ---
// These interfaces strictly mirror the Pydantic models in the Python Backend.
// Keeping frontend/backend types in sync is crucial for data integrity.

interface Ingredient {
  name: string;
  quantity: string;
  unit_cost: number | null;
  source: "sysco_catalog" | "estimated" | "not_available";
  sysco_item_number: string | null;
}

interface LineItem {
  item_name: string;
  category: string;
  ingredients: Ingredient[];
  ingredient_cost_per_unit: number;
}

interface JobStatus {
  processed_count: number;
  total_items_in_state: number;
  status: "pending" | "in_progress" | "completed" | "failed";
  learnings: string;
  latest_items: LineItem[];
}

// Default state for the JSON editor to reduce friction for testing.
const DEFAULT_JSON = JSON.stringify({
  "event": "Demo Event",
  "items": [
    { "name": "Bacon Scallops", "description": "Wrapped in applewood bacon", "category": "appetizers" }
  ]
}, null, 2);

// Visual Logic: Distinguish between verified Sysco data vs. AI Estimates.
const getBadgeColor = (source: string) => {
  switch (source) {
    case "sysco_catalog": return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "estimated": return "bg-amber-100 text-amber-800 border-amber-200";
    default: return "bg-red-100 text-red-800 border-red-200";
  }
};

export default function Dashboard() {
  const queryClient = useQueryClient();
  
  // UI State Management
  const [inputMode, setInputMode] = useState<"json" | "chat">("json");
  const [jsonInput, setJsonInput] = useState(DEFAULT_JSON);
  const [chatInput, setChatInput] = useState("");

  // --- MUTATION: START JOB ---
  // Handles the trigger for both JSON (Direct) and Chat (NLP Parsed) modes.
  const mutation = useMutation({
    mutationFn: async () => {
      // Branch logic based on input mode to hit the correct endpoint pipeline
      if (inputMode === "json") {
        const parsed = JSON.parse(jsonInput);
        // Robustness: Handle direct arrays or nested category structures
        const items = parsed.items || parsed.categories?.appetizers || [];
        return axios.post(`${API_URL}/api/estimate`, { items, reset: true });
      } else {
        // Chat Mode: Send raw text to the NLP pipeline
        return axios.post(`${API_URL}/api/estimate-text`, { text: chatInput, reset: true });
      }
    },
    onSuccess: () => {
      // UX: Immediately invalidate cache to show "Processing" state without waiting for next poll
      queryClient.invalidateQueries({ queryKey: ["jobStatus"] });
    },
    onError: (err) => {
      alert("Error initiating job. Check console.");
      console.error(err);
    }
  });

  // --- QUERY: SMART POLLING ---
  // Architecture Decision: Using Short Polling instead of WebSockets.
  // Reasons: Simpler to implement, more robust across firewalls/proxies, 
  // and sufficient for the 2-second update frequency requirement.
  const { data: statusData, isLoading: isStatusLoading } = useQuery({
    queryKey: ["jobStatus"],
    queryFn: async () => {
      const res = await axios.get<JobStatus>(`${API_URL}/api/status`);
      return res.data;
    },
    // Dynamic Polling Interval:
    // Only poll when the job is actually running. Stop polling when completed/failed.
    // This saves bandwidth and server resources.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "in_progress" ? 2000 : false;
    },
    refetchOnWindowFocus: false,
  });

  // Derived state for UI loading indicators
  const isProcessing = statusData?.status === "in_progress" || mutation.isPending;

  return (
    <div className="min-h-screen font-sans p-6 max-w-7xl mx-auto bg-slate-50/50">
      
      {/* HEADER */}
      <header className="flex items-center justify-between mb-8 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 text-white p-3 rounded-xl shadow-lg shadow-blue-200">
            <FaKitchenSet size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Yes Chef AI</h1>
            <p className="text-slate-500 text-sm font-medium">Catering Estimation Engine</p>
          </div>
        </div>
        
        {/* STATUS INDICATOR: "Alive" Visualization */}
        <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-full border border-slate-200 shadow-sm">
          <div className="relative flex items-center justify-center">
            {/* Animation Logic: Pulse when working, Static Glow when ready */}
            {isProcessing && <span className="absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75 animate-ping"></span>}
            <div className={`w-3 h-3 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.2)] ${ 
              isProcessing ? 'bg-green-500' : 
              isStatusLoading ? 'bg-blue-400 animate-bounce' : 
              'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]'
            }`} />
          </div>
          <span className={`text-sm font-bold tracking-wide ${ 
            isProcessing ? 'text-green-600' :
            isStatusLoading ? 'text-blue-500' :
            'text-emerald-700'
          }`}>
            {isProcessing ? "AGENT WORKING..." : 
             isStatusLoading ? "CONNECTING..." : 
             "SYSTEM READY"}
          </span>
        </div>
      </header>

      <div className="mb-6 bg-amber-50 border border-amber-200 text-amber-800 px-4 py-2 rounded-lg text-xs flex gap-2 items-center">
        <FaTriangleExclamation />
        <span><strong>Demo Mode:</strong> Global State Persistence is active to demonstrate resumability across sessions.</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT COLUMN: INPUT CONTROLS */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden transition-all duration-300 group focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-300">
            
            {/* MODE SWITCHER TABS */}
            <div className="flex border-b border-slate-100 bg-slate-50/50 p-1 gap-1">
              <button
                onClick={() => setInputMode("json")}
                className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 rounded-lg transition-all ${
                  inputMode === "json" 
                    ? "bg-white text-blue-700 shadow-sm border border-slate-200" 
                    : "text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                }`}
              >
                <FaCode /> JSON Mode
              </button>
              <button
                onClick={() => setInputMode("chat")}
                className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 rounded-lg transition-all ${
                  inputMode === "chat" 
                    ? "bg-white text-indigo-600 shadow-sm border border-slate-200" 
                    : "text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                }`}
              >
                <FaMessage /> Chat Mode
              </button>
            </div>

            {/* INPUT AREA */}
            <div className="relative">
              {inputMode === "json" ? (
                // MODE A: Technical / Dev Mode
                <textarea 
                  className="w-full h-80 p-4 font-mono text-xs bg-white text-slate-600 outline-none resize-none placeholder:text-slate-300"
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder="{ items: [] }"
                  spellCheck={false}
                />
              ) : (
                // MODE B: Natural Language / PM Mode
                <textarea 
                  className="w-full h-80 p-5 text-sm bg-white text-slate-800 outline-none resize-none 
                  placeholder:text-slate-400 font-medium leading-relaxed
                  selection:bg-indigo-100 selection:text-indigo-900" 
                  placeholder="Hi Chef! Describe your event menu here. Example: 'I need a quote for a wedding of 200 guests. We want Filet Mignon, Lobster Bisque, and Lava Cake.'"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                />
              )}
            </div>

            {/* START BUTTON */}
            <div className="p-4 bg-slate-50 border-t border-slate-100">
              <button
                onClick={() => mutation.mutate()}
                disabled={isProcessing || (inputMode === 'chat' && !chatInput)}
                className={`w-full py-3 px-4 cursor-pointer rounded-xl font-bold text-white flex items-center justify-center gap-2 transition-all shadow-lg hover:-translate-y-0.5 active:translate-y-0 ${
                  isProcessing 
                    ? "bg-slate-400 cursor-not-allowed shadow-none" 
                    : inputMode === "json"
                      ? "bg-blue-600 hover:bg-blue-700 shadow-blue-200"
                      : "bg-indigo-600 hover:bg-indigo-700 shadow-indigo-200"
                }`}
              >
                {isProcessing ? <FaRotate className="animate-spin" /> : <FaPlay />}
                {isProcessing ? "Chef is Cooking..." : "Start Estimation"}
              </button>
            </div>
          </div>

          {/* AI "BRAIN" VISUALIZATION */}
          {/* Displays the Context Compaction (Learnings) from the Backend */}
          <div className="bg-slate-900 rounded-2xl p-5 shadow-xl text-white border border-slate-800">
            <h3 className="text-indigo-400 font-bold text-xs uppercase tracking-wider mb-3 flex items-center gap-2">
              <FaMicrochip /> Agent Memory
            </h3>
            <div className="text-xs font-mono text-slate-300 leading-relaxed min-h-[60px]">
              {statusData?.learnings || "Waiting for execution..."}
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN: REAL-TIME FEED */}
        <div className="lg:col-span-8">
           
           {/* Skeleton Loader during Initial Fetch */}
           {isStatusLoading && (
             <div className="space-y-4 animate-pulse">
               {[1, 2].map((i) => (
                 <div key={i} className="bg-white h-32 rounded-2xl border border-slate-100"></div>
               ))}
             </div>
           )}

          <div className="space-y-5">
            {statusData?.latest_items && statusData.latest_items.length > 0 ? (
              // Reverse map to show newest items at the top
              [...statusData.latest_items].reverse().map((item, idx) => (
                <div key={idx} className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden">
                  
                  {/* Result Card Header */}
                  <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-start bg-slate-50/50">
                    <div>
                      <h3 className="font-bold text-lg text-slate-800">{item.item_name}</h3>
                      <span className="inline-block mt-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded shadow-sm">
                        {item.category}
                      </span>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-black text-slate-800 tracking-tight">
                        ${item.ingredient_cost_per_unit.toFixed(2)}
                      </p>
                      <p className="text-xs text-slate-400 font-medium">Cost / Srv</p>
                    </div>
                  </div>

                  {/* Ingredient Breakdown Table */}
                  <div className="p-0">
                    <table className="w-full text-sm text-left">
                      <thead className="bg-white text-slate-400 font-medium text-xs uppercase border-b border-slate-100">
                        <tr>
                          <th className="px-6 py-3 w-1/2">Ingredient</th>
                          <th className="px-6 py-3 text-right">Qty</th>
                          <th className="px-6 py-3 text-right">Cost</th>
                          <th className="px-6 py-3 text-right">Source</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50">
                        {item.ingredients.map((ing, i) => (
                          <tr key={i} className="hover:bg-slate-50/80 transition-colors">
                            <td className="px-6 py-3 font-medium text-slate-700">{ing.name}</td>
                            <td className="px-6 py-3 text-right text-slate-500">{ing.quantity}</td>
                            <td className="px-6 py-3 text-right font-mono text-slate-600">
                              {ing.unit_cost ? `$${ing.unit_cost.toFixed(2)}` : "—"}
                            </td>
                            <td className="px-6 py-3 text-right">
                              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${getBadgeColor(ing.source)}`}>
                                {ing.source === 'sysco_catalog' && <FaCheck />}
                                {ing.source === 'estimated' && <FaTriangleExclamation />}
                                {ing.source.replace('_', ' ').toUpperCase()}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))
            ) : (
              // Empty State
              !isStatusLoading && (
                <div className="py-20 text-center border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/30">
                  <FaListCheck className="mx-auto text-slate-300 text-5xl mb-4" />
                  <p className="text-slate-500 font-medium">No estimates yet.</p>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
