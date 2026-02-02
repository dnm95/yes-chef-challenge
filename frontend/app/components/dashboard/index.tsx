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
  FaListCheck 
} from "react-icons/fa6";

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

const DEFAULT_MENU = {
  "event": "Tech Challenge Demo",
  "items": [
    {
      "name": "Bacon-Wrapped Scallops",
      "description": "Pan-seared diver scallops wrapped in applewood-smoked bacon",
      "category": "appetizers"
    },
    {
      "name": "Wagyu Beef Tartare",
      "description": "A5 Wagyu beef, quail egg, capers, truffle oil, crostini",
      "category": "appetizers"
    }
  ]
};

export default function Dashboard() {
  const [jsonInput, setJsonInput] = useState(JSON.stringify(DEFAULT_MENU, null, 2));
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      const parsed = JSON.parse(jsonInput);
      const items = parsed.items || parsed.categories?.appetizers || [];
      return axios.post("http://127.0.0.1:8000/api/estimate", { items, reset: true });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobStatus"] });
    },
    onError: (err) => {
      alert("Error conectando con el Backend. Revisa la terminal.");
      console.error(err);
    }
  });

  const { data: statusData, isLoading: isStatusLoading } = useQuery({
    queryKey: ["jobStatus"],
    queryFn: async () => {
      const res = await axios.get<JobStatus>("http://127.0.0.1:8000/api/status");
      return res.data;
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "in_progress" ? 2000 : false;
    },
    refetchOnWindowFocus: false,
  });

  const isProcessing = statusData?.status === "in_progress" || mutation.isPending;

  const getBadgeColor = (source: string) => {
    switch (source) {
      case "sysco_catalog": return "bg-emerald-100 text-emerald-800 border-emerald-200";
      case "estimated": return "bg-amber-100 text-amber-800 border-amber-200";
      default: return "bg-red-100 text-red-800 border-red-200";
    }
  };

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
          <div className={`w-3 h-3 rounded-full ${isProcessing ? 'bg-green-500 animate-pulse' : 'bg-slate-300'}`} />
          <span className="text-sm font-semibold text-slate-600">
            {isProcessing ? "AGENT WORKING..." : "SYSTEM READY"}
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-1 overflow-hidden">
            <div className="bg-slate-50 px-4 py-3 border-b border-slate-100 flex justify-between items-center">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                <FaListCheck /> Menu JSON
              </span>
            </div>
            <textarea 
              className="w-full h-80 p-4 font-mono text-xs bg-white text-slate-600 outline-none resize-none focus:bg-slate-50 transition-colors"
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              spellCheck={false}
            />
            <div className="p-4 bg-slate-50 border-t border-slate-100">
              <button
                onClick={() => mutation.mutate()}
                disabled={isProcessing}
                className={`w-full py-3 px-4 rounded-xl font-bold text-white flex items-center justify-center gap-2 transition-all shadow-md ${
                  isProcessing 
                    ? "bg-slate-400 cursor-not-allowed" 
                    : "bg-blue-600 hover:bg-blue-700 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                }`}
              >
                {isProcessing ? <FaRotate className="animate-spin" /> : <FaPlay />}
                {isProcessing ? "Cooking..." : "Start Estimation"}
              </button>
            </div>
          </div>

          <div className="bg-slate-900 rounded-2xl p-5 shadow-xl text-white">
            <h3 className="text-purple-400 font-bold text-xs uppercase tracking-wider mb-3 flex items-center gap-2">
              <FaMicrochip /> Active Learnings
            </h3>
            <div className="text-xs font-mono text-slate-300 leading-relaxed min-h-[60px]">
              {statusData?.learnings || "No learnings yet. Waiting for agent execution..."}
            </div>
          </div>

        </div>

        <div className="lg:col-span-8">
          
          {isProcessing && statusData && (
            <div className="mb-6 bg-white p-4 rounded-xl border border-blue-100 shadow-sm animate-pulse">
              <div className="flex justify-between text-sm mb-2 font-medium">
                <span className="text-blue-700">Estimating Batch...</span>
                <span className="text-slate-500">{statusData.processed_count} Items Processed</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 w-1/2 animate-progress-indeterminate"></div>
              </div>
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
                          <th className="px-6 py-3">Qty</th>
                          <th className="px-6 py-3 text-right">Unit Cost</th>
                          <th className="px-6 py-3 text-right">Source</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50">
                        {item.ingredients.map((ing, i) => (
                          <tr key={i} className="hover:bg-slate-50/80 transition-colors">
                            <td className="px-6 py-3">
                              <div className="font-medium text-slate-700">{ing.name}</div>
                              {ing.sysco_item_number && (
                                <div className="text-[10px] font-mono text-slate-400">#{ing.sysco_item_number}</div>
                              )}
                            </td>
                            <td className="px-6 py-3 text-slate-500">{ing.quantity}</td>
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
              <div className="py-20 text-center border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/50">
                <FaKitchenSet className="mx-auto text-slate-300 text-5xl mb-4" />
                <p className="text-slate-500 font-medium">Ready for your orders, Chef.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
