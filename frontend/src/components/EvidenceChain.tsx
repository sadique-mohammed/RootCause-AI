"use client";

import { EvidenceItem } from "@/lib/api";
import { Terminal, Check, ShieldAlert, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="glass-panel border border-[var(--color-panel-border)] rounded-xl overflow-hidden transition-all duration-300">
      <div 
        className="p-4 flex items-start gap-4 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className={`mt-1 shrink-0 flex items-center justify-center w-8 h-8 rounded-full ${item.supports_conclusion ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-800 text-gray-400'}`}>
          {item.supports_conclusion ? <Check size={16} /> : <span className="font-mono text-xs">{item.step_number}</span>}
        </div>
        
        <div className="flex-grow">
          <div className="flex justify-between items-start">
            <h4 className="font-medium text-gray-200">
              {item.key_finding}
            </h4>
            <div className="text-gray-500 ml-4 shrink-0">
              {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </div>
          </div>
          <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-black/40 border border-gray-800 text-xs font-mono text-[var(--color-brand-cyan)]">
            <Terminal size={12} />
            {item.tool_name}({JSON.stringify(item.tool_args)})
          </div>
        </div>
      </div>
      
      {expanded && (
        <div className="border-t border-gray-800/50 bg-black/30 p-4">
          <div className="mb-4">
            <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Relevance</h5>
            <p className="text-sm text-gray-300 leading-relaxed border-l-2 border-gray-700 pl-3">
              {item.relevance}
            </p>
          </div>
          
          <div>
            <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <ShieldAlert size={14} /> Raw Output
            </h5>
            <div className="bg-[#0c0c0c] p-3 rounded-lg border border-gray-800/80 max-h-64 overflow-y-auto">
              <pre className="text-xs font-mono text-gray-400 whitespace-pre-wrap break-words">
                {item.raw_output}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EvidenceChain({ evidence }: { evidence: EvidenceItem[] }) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="w-full max-w-4xl mx-auto mt-8 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-150 fill-mode-both">
      <h3 className="text-lg font-semibold tracking-tight mb-4 flex items-center gap-2">
        <span className="bg-white text-black text-xs font-bold px-2 py-0.5 rounded">LOG</span>
        Investigation Trail
      </h3>
      <div className="space-y-3 relative before:absolute before:inset-0 before:ml-[34px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-gray-800 before:to-transparent">
        {/* We use a simple vertical list instead of a complex alternating timeline for better readability with dense logs */}
        {evidence.map((item) => (
          <div key={item.id} className="relative z-10">
            <EvidenceCard item={item} />
          </div>
        ))}
      </div>
    </div>
  );
}
