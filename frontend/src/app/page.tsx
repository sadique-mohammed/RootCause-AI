"use client";

import { useState, useEffect } from "react";
import IncidentInput from "@/components/IncidentInput";
import DiagnosisResult from "@/components/DiagnosisResult";
import EvidenceChain from "@/components/EvidenceChain";
import { api, DiagnosisRun, CommandLogItem } from "@/lib/api";
import { Activity } from "lucide-react";

export default function Home() {
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runData, setRunData] = useState<DiagnosisRun | null>(null);
  const [logs, setLogs] = useState<CommandLogItem[]>([]);

  useEffect(() => {
    if (!activeRunId) return;

    let interval: NodeJS.Timeout;
    
    const poll = async () => {
      try {
        const data = await api.getDiagnosis(activeRunId);
        setRunData(data);
        
        if (data.status === "running") {
          const liveLogs = await api.getCommandLogs(activeRunId);
          setLogs(liveLogs);
        }

        // Stop polling if completed, inconclusive, or failed
        if (["completed", "inconclusive", "failed"].includes(data.status)) {
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    };

    // Initial fetch immediately
    poll();
    
    // Poll every 3 seconds
    interval = setInterval(poll, 3000);
    
    return () => clearInterval(interval);
  }, [activeRunId]);

  return (
    <main className="min-h-screen p-4 md:p-8 pb-24">
      {/* Header */}
      <header className="max-w-4xl mx-auto flex items-center justify-between mb-12 mt-4">
        <div className="flex items-center gap-3">
          <div className="bg-[var(--color-brand-blue)]/20 p-2.5 rounded-xl border border-[var(--color-brand-blue)]/30 relative">
            <div className="absolute inset-0 bg-[var(--color-brand-cyan)]/20 blur-xl rounded-full animate-pulse" />
            <Activity className="text-[var(--color-brand-cyan)] relative z-10" size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
              RootCause AI
            </h1>
            <p className="text-xs text-[var(--color-brand-cyan)] font-mono tracking-widest uppercase">
              Autonomous SRE
            </p>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="space-y-8">
        {!activeRunId ? (
          <IncidentInput onStart={(id) => setActiveRunId(id)} />
        ) : (
          <>
            <div className="max-w-4xl mx-auto flex justify-end">
              <button 
                onClick={() => {
                  setActiveRunId(null);
                  setRunData(null);
                }}
                className="text-xs text-gray-400 hover:text-white transition-colors flex items-center gap-1 border border-gray-800 rounded-md px-3 py-1 bg-black/50"
              >
                Start New Investigation
              </button>
            </div>
            {runData && <DiagnosisResult run={runData} liveLogs={logs} />}
            {runData?.evidence && <EvidenceChain evidence={runData.evidence} />}
          </>
        )}
      </div>
    </main>
  );
}
