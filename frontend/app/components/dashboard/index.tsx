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
  FaListCheck,
  FaMessage,
  FaCode
} from "react-icons/fa6";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

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

const DEFAULT_JSON = JSON.stringify({
  "event": "Demo Event",
  "items": [
    { "name": "Bacon Scallops", "description": "Wrapped in applewood bacon", "category": "appetizers" }
  ]
}, null, 2);

const getBadgeColor = (source: string) => {
  switch (source) {
    case "sysco_catalog": return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "estimated": return "bg-amber-100 text-amber-800 border-amber-200";
    default: return "bg-red-100 text-red-800 border-red-200";
  }
};

export default function Dashboard() {
  const queryClient = useQueryClient();
  
  const [inputMode, setInputMode] = useState<"json" | "chat">("json");
  const [jsonInput, setJsonInput] = useState(DEFAULT_JSON);
  const [chatInput, setChatInput] = useState("");

  const mutation = useMutation({
    mutationFn: async () => {
      if (inputMode === "json") {
        const parsed = JSON.parse(jsonInput);
        const items = parsed.items || parsed.categories?.appetizers || [];
        return axios.post(`${API_URL}/api/estimate`, { items, reset: true });
      } else {
        return axios.post(`${API_URL}/api/estimate-text`, { text: chatInput, reset: true });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobStatus"] });
    },
    onError: (err) => {
      alert("Error initiating job. Check console.");
      console.error(err);
    }
  });

  const { data: statusData, isLoading: isStatusLoading } = useQuery({
    queryKey: ["jobStatus"],
    queryFn: async () => {
      const res = await axios.get<JobStatus>(`${API_URL}/api/status`);
      return res.data;
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "in_progress" ? 2000 : false;
    },
    refetchOnWindowFocus: false,
  });

  const isProcessing = statusData?.status === "in_progress" || mutation.isPending;

  return (
    <div className="min-h-screen font-sans p-6 max-w-7xl mx-auto">
      
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
        
        <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-full border border-slate-200 shadow-sm">
          <div className={`w-3 h-3 rounded-full ${
            isProcessing ? 'bg-green-500 animate-pulse' : 
            isStatusLoading ? 'bg-blue-400 animate-bounce' : 
            'bg-slate-300'
          }`} />
          <span className="text-sm font-semibold text-slate-600">
            {isProcessing ? "AGENT WORKING..." : 
             isStatusLoading ? "CONNECTING..." : 
             "SYSTEM READY"}
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden transition-all duration-300">
            
            <div className="flex border-b border-slate-100">
              <button
                onClick={() => setInputMode("json")}
                className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${
                  inputMode === "json" 
                    ? "bg-slate-50 text-blue-600 border-b-2 border-blue-600" 
                    : "text-slate-400 hover:text-slate-600 hover:bg-slate-50"
                }`}
              >
                <FaCode /> JSON Mode
              </button>
              <button
                onClick={() => setInputMode("chat")}
                className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${
                  inputMode === "chat" 
                    ? "bg-purple-50 text-purple-600 border-b-2 border-purple-600" 
                    : "text-slate-400 hover:text-slate-600 hover:bg-slate-50"
                }`}
              >
                <FaMessage /> Chat Mode
              </button>
            </div>

            <div className="relative">
              {inputMode === "json" ? (
                <textarea 
                  className="w-full h-80 p-4 font-mono text-xs bg-white text-slate-600 outline-none resize-none focus:bg-slate-50 transition-colors"
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder="{ items: [] }"
                  spellCheck={false}
                />
              ) : (
                <textarea 
                  className="w-full h-80 p-5 text-sm bg-white text-slate-700 outline-none resize-none placeholder:text-slate-300 focus:bg-purple-50/10 transition-colors"
                  placeholder="Example: I need a quote for a wedding of 200 guests. We want Filet Mignon for the main course, Lobster Bisque to start, and a Chocolate Lava Cake for dessert."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                />
              )}
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-100">
              <button
                onClick={() => mutation.mutate()}
                disabled={isProcessing || (inputMode === 'chat' && !chatInput)}
                className={`w-full py-3 px-4 rounded-xl font-bold text-white flex items-center justify-center gap-2 transition-all shadow-md ${
                  isProcessing 
                    ? "bg-slate-400 cursor-not-allowed" 
                    : inputMode === "json"
                      ? "bg-blue-600 hover:bg-blue-700 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                      : "bg-purple-600 hover:bg-purple-700 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                }`}
              >
                {isProcessing ? <FaRotate className="animate-spin" /> : <FaPlay />}
                {isProcessing ? "Chef is Cooking..." : "Start Estimation"}
              </button>
            </div>
          </div>

          <div className="bg-slate-900 rounded-2xl p-5 shadow-xl text-white">
            <h3 className="text-purple-400 font-bold text-xs uppercase tracking-wider mb-3 flex items-center gap-2">
              <FaMicrochip /> Agent Memory
            </h3>
            <div className="text-xs font-mono text-slate-300 leading-relaxed min-h-15">
              {statusData?.learnings || "Waiting for execution..."}
            </div>
          </div>

        </div>

        <div className="lg:col-span-8">
           {isStatusLoading && (
             <div className="space-y-4 animate-pulse">
               {[1, 2].map((i) => (
                 <div key={i} className="bg-white h-32 rounded-2xl border border-slate-100"></div>
               ))}
             </div>
           )}

          <div className="space-y-5">
            {statusData?.latest_items && statusData.latest_items.length > 0 ? (
              [...statusData.latest_items].reverse().map((item, idx) => (
                <div key={idx} className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden">
                  <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-start bg-slate-50/50">
                    <div>
                      <h3 className="font-bold text-lg text-slate-800">{item.item_name}</h3>
                      <span className="inline-block mt-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-200/50 px-2 py-0.5 rounded">
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
              !isStatusLoading && (
                <div className="py-20 text-center border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/50">
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
