export const API_BASE = "http://localhost:8000/api/v1";

export interface EvidenceItem {
  id: string;
  step_number: number;
  tool_name: string;
  tool_args: any;
  raw_output: string;
  key_finding: string;
  relevance: string;
  supports_conclusion: boolean;
}

export interface DiagnosisRun {
  id: string;
  target_host: string;
  incident_description: string;
  status: "pending" | "running" | "completed" | "inconclusive" | "failed";
  root_cause: string | null;
  root_cause_category: string | null;
  confidence: number | null;
  suggested_fix: string | null;
  summary: string | null;
  evidence: EvidenceItem[];
  created_at: string;
  completed_at: string | null;
}

export interface CommandLogItem {
  id: string;
  run_id: string;
  command: string;
  args: any;
  exit_code: number;
  duration_ms: number;
  allowed: boolean;
  executed_at: string;
}

export interface IncidentCatalogItem {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: string;
  seed_script_path: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_provider: string | null;
  llm_model: string | null;
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error("Failed to check health");
    return res.json() as Promise<HealthResponse>;
  },

  async getCatalog() {
    const res = await fetch(`${API_BASE}/incidents/catalog`);
    if (!res.ok) throw new Error("Failed to get incident catalog");
    return res.json() as Promise<IncidentCatalogItem[]>;
  },

  async seedIncident(incidentId: string) {
    const res = await fetch(`${API_BASE}/incidents/seed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident_id: incidentId }),
    });
    if (!res.ok) throw new Error("Failed to seed incident");
    return res.json();
  },

  async startDiagnosis(host: string, description: string) {
    const res = await fetch(`${API_BASE}/diagnose`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_host: host,
        incident_description: description,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to start diagnosis");
    }
    return res.json() as Promise<{ run_id: string; status: string }>;
  },

  async getDiagnosis(id: string) {
    const res = await fetch(`${API_BASE}/diagnose/${id}`);
    if (!res.ok) throw new Error("Failed to get diagnosis");
    return res.json() as Promise<DiagnosisRun>;
  },

  async getCommandLogs(id: string) {
    const res = await fetch(`${API_BASE}/diagnose/${id}/commands`);
    if (!res.ok) throw new Error("Failed to get command logs");
    return res.json() as Promise<CommandLogItem[]>;
  }
};
