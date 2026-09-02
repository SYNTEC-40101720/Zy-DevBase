export type JobStatus =
  | "queued"
  | "running"
  | "completed"
  | "cancelled"
  | "failed";

export type EventKind =
  | "job_created"
  | "job_started"
  | "progress"
  | "job_completed"
  | "job_cancelled"
  | "job_failed";

export interface HealthResponse {
  status: "ok";
  service: string;
  active_job_id: string | null;
  window_close_mode: "stop_on_close" | "continue_on_close";
}

export interface Job {
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

export interface Snapshot {
  job: Job | null;
  events: RuntimeEvent[];
  event_cursor: number;
}

export interface CalcHistoryItem {
  expression: string;
  result: string;
}

export interface CalcState {
  display: string;
  expression: string[];
  error: boolean;
  memory: string[];
  history: CalcHistoryItem[];
}

export type SocketMessage =
  | { type: "health"; data: HealthResponse }
  | { type: "snapshot"; data: Snapshot }
  | { type: "event"; data: RuntimeEvent };