import { useSyncExternalStore } from "react";

import type { ConnectionStatus, ToolDescriptor, UpdateStatus } from "../api/types";

export interface WorkbenchState {
  tools: ToolDescriptor[];
  selectedTool: string | null;
  connection: ConnectionStatus;
  bottomPanelOpen: boolean;
  updateStatus: UpdateStatus;
}

type Listener = () => void;

const initialState: WorkbenchState = {
  tools: [],
  selectedTool: null,
  connection: "idle",
  bottomPanelOpen: false,
  updateStatus: "idle",
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
};

export function useWorkbenchStore(): WorkbenchState {
  return useSyncExternalStore(
    workbenchStore.subscribe,
    workbenchStore.getSnapshot,
    workbenchStore.getSnapshot,
  );
}
