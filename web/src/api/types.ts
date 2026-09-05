export type JobStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "succeeded"
  | "completed_with_warnings"
  | "cancelled"
  | "failed";

export type EventKind =
  | "job_created"
  | "job_started"
  | "progress"
  | "job_cancelling"
  | "job_succeeded"
  | "job_completed_with_warnings"
  | "job_cancelled"
  | "job_failed";

export interface ToolDescriptor {
  kind: string;
  title: string;
  subtitle: string | null;
  group: string;
  glyph: string;
  access_key: string | null;
  supports_input: boolean;
  mode: string;
}

export interface ToolListResponse {
  tools: ToolDescriptor[];
}

export interface JobResponse {
  id: string;
  kind: string;
  status: JobStatus;
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
}

export interface RuntimeEvent {
  sequence: number;
  event_id: string;
  job_id: string;
  kind: EventKind;
  status: JobStatus;
  progress: number;
  message: string;
  created_at: string;
}

export interface RuntimeSnapshot {
  job: JobResponse | null;
  events: RuntimeEvent[];
  event_cursor: number;
}

export interface HealthResponse {
  status: "ok";
  service: string;
  active_job_id: string | null;
  window_close_mode: "stop_on_close" | "continue_on_close";
}

export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnected"
  | "unauthorized";

export type UpdateStatus =
  | "idle"
  | "checking"
  | "available"
  | "up_to_date"
  | "downloading"
  | "applying"
  | "succeeded"
  | "rollback"
  | "error";

export interface UpdateCheckResponse {
  current: string;
  latest: string | null;
  available: boolean;
  installable: boolean;
  asset_name: string | null;
  release_url: string | null;
  error: string | null;
}

export interface UpdateProgressResponse {
  status: string;
  percent: number;
  message: string;
  error: string | null;
  rollback: boolean;
  ready_file: string | null;
}
