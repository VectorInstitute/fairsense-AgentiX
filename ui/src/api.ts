export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export type WorkflowID = "bias_text" | "bias_image" | "risk";

export interface HealthResponse {
  status: string;
  llm_provider: string;
  mock_mode: boolean;
}

export async function health(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/v1/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.statusText}`);
  }
  return res.json();
}

export interface AnalyzePayload {
  content: string;
  input_type?: WorkflowID;
  options?: Record<string, unknown>;
}

export interface AnalyzeStartResponse {
  run_id: string;
  status: string;
  message: string;
}

export async function analyze(payload: AnalyzePayload) {
  const res = await fetch(`${API_BASE}/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function analyzeStart(payload: AnalyzePayload): Promise<AnalyzeStartResponse> {
  const res = await fetch(`${API_BASE}/v1/analyze/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function analyzeFile(file: File, inputType?: WorkflowID) {
  const form = new FormData();
  form.append("file", file);
  if (inputType) {
    form.append("input_type", inputType);
  }
  const res = await fetch(`${API_BASE}/v1/analyze/upload`, {
    method: "POST",
    body: form
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function analyzeFileStart(file: File, inputType?: WorkflowID): Promise<AnalyzeStartResponse> {
  const form = new FormData();
  form.append("file", file);
  if (inputType) {
    form.append("input_type", inputType);
  }
  const res = await fetch(`${API_BASE}/v1/analyze/upload/start`, {
    method: "POST",
    body: form
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.statusText}`);
  }
  return res.json();
}

export function connectToStream(runId: string, onEvent: (event: MessageEvent) => void) {
  const url = new URL(`/v1/stream/${runId}`, API_BASE);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(url.toString());
  ws.onmessage = onEvent;
  return ws;
}
