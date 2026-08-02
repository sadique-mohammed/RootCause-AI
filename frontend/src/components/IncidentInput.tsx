"use client";

import { useState, useEffect } from "react";
import { Terminal, Play, Server, AlertCircle, Brain } from "lucide-react";
import { api, IncidentCatalogItem, HealthResponse } from "@/lib/api";

interface IncidentInputProps {
  onStart: (runId: string) => void;
}

export default function IncidentInput({ onStart }: IncidentInputProps) {
  const [host, setHost] = useState("192.168.252.2");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [seedId, setSeedId] = useState("");
  const [seedStatus, setSeedStatus] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<IncidentCatalogItem[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    api.getCatalog().then(setCatalog).catch(err => console.error("Failed to load catalog", err));
    api.getHealth().then(setHealth).catch(err => console.error("Failed to load health", err));
  }, []);

  const handleSeed = async () => {
    if (!seedId) return;
    setSeedStatus("Seeding...");
    try {
      await api.seedIncident(seedId);
      setSeedStatus(`Incident ${seedId} seeded successfully!`);
      setTimeout(() => setSeedStatus(null), 3000);
    } catch (err: any) {
      setSeedStatus(`Seed failed: ${err.message}`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim() || !host.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await api.startDiagnosis(host, description);
      onStart(res.run_id);
    } catch (err: any) {
      alert(`Failed to start: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 md:p-8 flex flex-col gap-6 w-full max-w-4xl mx-auto mt-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center gap-3 border-b border-[var(--color-panel-border)] pb-4">
        <div className="p-2 bg-blue-500/20 rounded-lg">
          <Terminal className="text-[var(--color-brand-cyan)]" size={24} />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">New Investigation</h2>
          <p className="text-sm text-gray-400">Provide details for the AI agent to diagnose the issue.</p>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Left Column - Lab Controls */}
        <div className="w-full md:w-1/3 flex flex-col gap-4">
          <div className="glass-panel p-4 rounded-xl border border-dashed border-gray-700 bg-black/20">
            <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2 mb-3">
              <Server size={16} /> Target Lab VM
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Hostname / IP</label>
                <input
                  type="text"
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  className="w-full glass-input rounded-lg px-3 py-2 text-sm text-gray-200"
                  placeholder="192.168.x.x"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Seed Test Incident</label>
                <div className="flex gap-2">
                  <select 
                    className="w-full glass-input rounded-lg px-3 py-2 text-sm text-gray-200 cursor-pointer"
                    value={seedId}
                    onChange={(e) => {
                      setSeedId(e.target.value);
                      const selected = catalog.find(i => i.id === e.target.value);
                      if (selected) setDescription(selected.description);
                    }}
                  >
                    <option value="" className="bg-gray-900 text-gray-400">Select...</option>
                    {catalog.map(item => (
                      <option key={item.id} value={item.id} className="bg-gray-900">
                        {item.id}: {item.name}
                      </option>
                    ))}
                  </select>
                  <button 
                    type="button"
                    onClick={handleSeed}
                    disabled={!seedId}
                    className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-[var(--color-panel-border)]"
                  >
                    Seed
                  </button>
                </div>
                {seedStatus && (
                  <p className={`text-xs mt-2 ${seedStatus.includes('failed') ? 'text-red-400' : 'text-green-400'}`}>
                    {seedStatus}
                  </p>
                )}
              </div>
            </div>
          </div>
          
          <div className="glass-panel p-4 rounded-xl border border-dashed border-gray-700 bg-black/20">
            <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2 mb-3">
              <Brain size={16} /> Active AI Model
            </h3>
            <div className="text-sm text-gray-400">
              {health ? (
                <div>
                  <p className="mb-1"><strong>Provider:</strong> <span className="text-[var(--color-brand-cyan)] uppercase">{health.llm_provider}</span></p>
                  <p><strong>Model:</strong> <span className="text-gray-200">{health.llm_model}</span></p>
                </div>
              ) : (
                <p className="text-gray-500 animate-pulse">Detecting model...</p>
              )}
            </div>
          </div>
        </div>

        {/* Right Column - Investigation Details */}
        <div className="w-full md:w-2/3">
          <form onSubmit={handleSubmit} className="flex flex-col h-full gap-4">
            <div className="flex-grow">
              <label className="text-sm font-medium text-gray-300 flex items-center gap-2 mb-2">
                <AlertCircle size={16} /> Incident Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. Users are reporting that they cannot upload files to the server, and background cron jobs are failing with write errors..."
                className="w-full h-32 md:h-full glass-input rounded-xl p-4 text-sm resize-none focus:ring-0 focus:outline-none placeholder-gray-600 transition-shadow"
                required
              />
            </div>
            
            <button
              type="submit"
              disabled={isSubmitting || !description.trim()}
              className="group relative flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-gradient-to-r from-[var(--color-brand-blue)] to-[var(--color-brand-cyan)] text-white font-semibold transition-all hover:shadow-[0_0_20px_rgba(0,240,255,0.4)] disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"></div>
              <span className="relative z-10 flex items-center gap-2">
                {isSubmitting ? "Initiating Diagnosis..." : "Start Investigation"}
                {!isSubmitting && <Play size={18} fill="currentColor" />}
              </span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
