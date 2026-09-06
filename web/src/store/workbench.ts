import { useSyncExternalStore } from "react";

import type {
  ConnectionStatus,
  JobResponse,
  RuntimeEvent,
  ToolDescriptor,
  UpdateStatus,
} from "../api/types";

export interface WorkbenchState {
  tools: ToolDescriptor[];
  selectedTool: string | null;
  connection: ConnectionStatus;
  bottomPanelOpen: boolean;
  updateStatus: UpdateStatus;
  currentJob: JobResponse | null;
  events: RuntimeEvent[];
}

type Listener = () => void;

const MAX_EVENTS = 200;

const initialState: WorkbenchState = {
  tools: [],
  selectedTool: null,
  connection: "idle",
  bottomPanelOpen: false,
  updateStatus: "idle",
  currentJob: null,
  events: [],
};

let state = initialState;
const listeners = new Set<Listener>();

export const workbenchStore = {
  getSnapshot(): WorkbenchState {
    return state;
  },
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  patch(patch: Partial<WorkbenchState>): void {
    state = { ...state, ...patch };
    listeners.forEach((listener) => listener());
  },

  setSnapshot(snapshot: { job: JobResponse | null; events: RuntimeEvent[] }): void {
    const eventsBySequence = new Map(
      state.events.map((event) => [event.sequence, event]),
    );
    snapshot.events.forEach((event) => eventsBySequence.set(event.sequence, event));
    const events = [...eventsBySequence.values()]
      .sort((left, right) => left.sequence - right.sequence)
      .slice(-MAX_EVENTS);
    state = { ...state, currentJob: snapshot.job, events };
    listeners.forEach((listener) => listener());
  },

  pushEvent(event: RuntimeEvent): void {
    const events = [...state.events, event].slice(-MAX_EVENTS);
    const currentJob = state.currentJob?.id === event.job_id
      ? {
          ...state.currentJob,
          status: event.status,
          progress: event.progress,
          message: event.message,
          updated_at: event.created_at,
        }
      : state.currentJob;
    state = { ...state, currentJob, events };
    listeners.forEach((listener) => listener());
  },
};

export function useWorkbenchStore(): WorkbenchState {
  return useSyncExternalStore(
    workbenchStore.subscribe,
    workbenchStore.getSnapshot,
    workbenchStore.getSnapshot,
  );
}
