import { DiagnosisRun, CommandLogItem } from "@/lib/api";
import { CheckCircle2, AlertTriangle, XCircle, Loader2, Terminal } from "lucide-react";

export default function DiagnosisResult({ run, liveLogs = [] }: { run: DiagnosisRun, liveLogs?: CommandLogItem[] }) {
  const getStatusConfig = () => {
    switch (run.status) {
      case "running":
        return {
          icon: <Loader2 className="animate-spin text-blue-400" size={32} />,
          bg: "bg-blue-500/10",
          border: "border-blue-500/30",
          text: "text-blue-400",
          title: "Diagnosis in Progress"
        };
      case "completed":
        return {
          icon: <CheckCircle2 className="text-emerald-400" size={32} />,
          bg: "bg-emerald-500/10",
          border: "border-emerald-500/30",
          text: "text-emerald-400",
          title: "Root Cause Identified"
        };
      case "inconclusive":
        return {
          icon: <AlertTriangle className="text-amber-400" size={32} />,
          bg: "bg-amber-500/10",
          border: "border-amber-500/30",
          text: "text-amber-400",
          title: "Diagnosis Inconclusive"
        };
      case "failed":
      default:
        return {
          icon: <XCircle className="text-red-400" size={32} />,
          bg: "bg-red-500/10",
          border: "border-red-500/30",
          text: "text-red-400",
          title: "Diagnosis Failed"
        };
    }
  };

  const config = getStatusConfig();
  
  // Format confidence as percentage
  const confidenceScore = run.confidence ? Math.round(run.confidence * 100) : 0;
  
  return (
    <div className={`glass-panel rounded-2xl p-6 md:p-8 w-full max-w-4xl mx-auto border-t-4 border-t-[var(--color-brand-cyan)] animate-in fade-in zoom-in-95 duration-500`}>
      <div className="flex flex-col md:flex-row gap-6 items-start">
        {/* Status Indicator */}
        <div className={`flex items-center justify-center w-16 h-16 rounded-2xl ${config.bg} border ${config.border} shrink-0`}>
          {config.icon}
        </div>
        
        <div className="flex-grow space-y-4 w-full">
          <div>
            <h2 className={`text-2xl font-bold tracking-tight ${config.text}`}>
              {config.title}
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              Target: <code className="bg-black/30 px-2 py-0.5 rounded border border-gray-800">{run.target_host}</code>
            </p>
          </div>
          
          {run.status === "running" ? (
            <div className="space-y-4">
              <div className="glass-panel bg-black/40 p-4 rounded-xl border border-gray-800/50 relative overflow-hidden">
                <div className="absolute top-0 left-0 h-1 bg-[var(--color-brand-blue)]/50 w-full">
                  <div className="h-full bg-[var(--color-brand-cyan)] w-1/3 animate-[pulse_2s_ease-in-out_infinite,slide_2s_linear_infinite]" 
                       style={{animation: 'pulse 2s ease-in-out infinite, slide 2s linear infinite'}} />
                </div>
                <p className="text-gray-300 font-mono text-sm flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-[var(--color-brand-cyan)] animate-ping" />
                  The AI is currently investigating the system state...
                </p>
              </div>

              <div className="glass-panel p-4 rounded-xl border border-gray-800 bg-black/60 font-mono text-xs text-gray-400">
                <h4 className="text-gray-500 mb-2 flex items-center gap-2">
                  <Terminal size={14} /> Live Investigation Log
                </h4>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                  {/* Always show initialization steps */}
                  <div className="flex gap-2">
                    <span className="text-gray-600">[{new Date().toLocaleTimeString()}]</span>
                    <span className="text-gray-300">[System] Initializing autonomous SRE agent...</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-gray-600">[{new Date().toLocaleTimeString()}]</span>
                    <span className="text-gray-300">[System] Connecting to target {run.target_host}...</span>
                  </div>
                  
                  {liveLogs.map((log) => (
                    <div key={log.id} className="flex gap-2">
                      <span className="text-gray-600">[{new Date(log.executed_at).toLocaleTimeString()}]</span>
                      <span className="text-[var(--color-brand-cyan)]">$ {log.command}</span>
                      {log.args && <span className="text-gray-300">{Array.isArray(log.args) ? log.args.join(' ') : log.args}</span>}
                      {log.exit_code === -1 && <span className="text-red-400 ml-2">(Blocked by allowlist)</span>}
                      {log.exit_code > 0 && <span className="text-amber-400 ml-2">(Exit {log.exit_code})</span>}
                    </div>
                  ))}
                  
                  {/* Status Indicator */}
                  <div className="flex gap-2 items-center mt-2">
                    <span className="text-gray-600">[{new Date().toLocaleTimeString()}]</span>
                    <span className="text-gray-400 animate-pulse italic">Agent is thinking and generating next action...</span>
                    <div className="animate-pulse w-2 h-3 bg-gray-500"></div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2 space-y-4">
                <div className="glass-panel p-5 rounded-xl border border-[var(--color-panel-border)] bg-black/20">
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Root Cause</h3>
                  <p className="text-lg text-white font-medium leading-snug">
                    {run.root_cause || "Could not conclusively determine root cause."}
                  </p>
                  {run.root_cause_category && (
                    <span className="inline-block mt-3 px-3 py-1 rounded-full bg-[var(--color-brand-purple)]/20 border border-[var(--color-brand-purple)]/30 text-[var(--color-brand-purple)] text-xs font-semibold tracking-wide">
                      {run.root_cause_category.toUpperCase()}
                    </span>
                  )}
                </div>
                
                {run.suggested_fix && (
                  <div className="glass-panel p-5 rounded-xl border border-[var(--color-panel-border)] bg-gradient-to-br from-blue-900/10 to-transparent">
                    <h3 className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">Suggested Fix</h3>
                    <p className="text-sm text-gray-300 leading-relaxed">
                      {run.suggested_fix}
                    </p>
                  </div>
                )}
              </div>
              
              <div className="glass-panel p-5 rounded-xl border border-[var(--color-panel-border)] flex flex-col items-center justify-center text-center">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Confidence</h3>
                <div className="relative flex items-center justify-center w-24 h-24">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-gray-800"
                      strokeWidth="3"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className={confidenceScore > 80 ? "text-emerald-400" : confidenceScore > 50 ? "text-amber-400" : "text-red-400"}
                      strokeDasharray={`${confidenceScore}, 100`}
                      strokeWidth="3"
                      strokeLinecap="round"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <div className="absolute text-2xl font-bold">
                    {confidenceScore}%
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Always show execution logs if we have them and it's not running (running state already shows them above) */}
          {run.status !== "running" && liveLogs.length > 0 && (
            <div className="mt-6 glass-panel p-4 rounded-xl border border-gray-800 bg-black/60 font-mono text-xs text-gray-400">
              <h4 className="text-gray-500 mb-2 flex items-center gap-2">
                <Terminal size={14} /> Execution Log
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                <div className="flex gap-2">
                  <span className="text-gray-600">[{new Date(run.created_at).toLocaleTimeString()}]</span>
                  <span className="text-gray-300">[System] Autonomous SRE agent initialized.</span>
                </div>
                {liveLogs.map((log) => (
                  <div key={log.id} className="flex gap-2">
                    <span className="text-gray-600">[{new Date(log.executed_at).toLocaleTimeString()}]</span>
                    <span className="text-[var(--color-brand-cyan)]">$ {log.command}</span>
                    {log.args && <span className="text-gray-300">{Array.isArray(log.args) ? log.args.join(' ') : log.args}</span>}
                    {log.exit_code === -1 && <span className="text-red-400 ml-2">(Blocked by allowlist)</span>}
                    {log.exit_code > 0 && <span className="text-amber-400 ml-2">(Exit {log.exit_code})</span>}
                  </div>
                ))}
                <div className="flex gap-2">
                  <span className="text-gray-600">[{new Date(run.completed_at || '').toLocaleTimeString()}]</span>
                  <span className="text-gray-300">[System] Investigation {run.status}.</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Required for the inline style slide animation above */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes slide {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(300%); }
        }
      `}} />
    </div>
  );
}
