import { createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { apiClient } from "../api/client";
import { workbenchStore } from "../store/workbench";
import type { UpdateCheckResponse } from "../api/types";

vi.mock("../components/DemoPanel", () => ({ DemoPanel: () => null }));

vi.mock("../api/events", () => ({
  RuntimeEventStream: class {
    connect() {}
    close() {}
  },
}));

const releaseUrl = "https://github.com/SYNTEC-40101720/Zy-DevBase/releases/tag/v99.0.0";
let root: Root;
let container: HTMLDivElement;

async function click(text: string) {
  const button = Array.from(container.querySelectorAll("button")).find(
    (item) => item.textContent?.trim() === text || item.getAttribute("aria-label") === text,
  );
  expect(button, `button ${text}`).toBeTruthy();
  await act(async () => button!.click());
}

beforeEach(async () => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  workbenchStore.patch({ tools: [], selectedTool: null, updateStatus: "idle", updateResult: null });
  apiClient.setToken("test-token");
  vi.spyOn(apiClient, "listTools").mockResolvedValue([]);
  vi.spyOn(apiClient, "checkUpdate").mockResolvedValue({
    current: "0.3.7", latest: "99.0.0", available: true,
    release_url: releaseUrl, error: null,
  });
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => root.render(createElement(App)));
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.restoreAllMocks();
});

describe("manual update notification", () => {
  it("does not check on startup and shows a manual release link in settings", async () => {
    const check = vi.spyOn(apiClient, "checkUpdate").mockResolvedValue({
      current: "0.3.7", latest: "99.0.0", available: true,
      release_url: releaseUrl, error: null,
    });
    await click("设置");
    expect(check).not.toHaveBeenCalled();
    await click("检查更新");
    expect(check).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain("发现新版本 v99.0.0");
    const link = container.querySelector<HTMLAnchorElement>("a.update-banner-action");
    expect(link?.href).toBe(releaseUrl);
    expect(link?.target).toBe("_blank");
    expect(link?.rel).toBe("noopener noreferrer");
    expect(container.textContent).not.toContain("准备更新");
    await click("返回工作台");
    expect(container.querySelector<HTMLAnchorElement>("a.update-banner-action")?.href).toBe(releaseUrl);
  });

  it("does not report latest when the server returns an offline error with HTTP 200", async () => {
    vi.spyOn(apiClient, "checkUpdate").mockResolvedValue({
      current: "0.3.7", latest: null, available: false, release_url: null, error: "offline",
    });
    await click("设置");
    await click("检查更新");
    expect(container.textContent).toContain("检查未完成");
    expect(container.textContent).not.toContain("当前无需更新");
    expect(container.querySelector("a.update-banner-action")).toBeNull();
  });

  it("handles transport failure and allows another attempt", async () => {
    vi.spyOn(apiClient, "checkUpdate")
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce({ current: "0.3.7", latest: "0.3.7", available: false, release_url: null, error: null });
    await click("设置");
    await click("检查更新");
    expect(container.textContent).toContain("检查未完成");
    await click("检查更新");
    expect(container.textContent).toContain("当前无需更新");
  });

  it("disables duplicate requests while checking", async () => {
    let resolve!: (result: UpdateCheckResponse) => void;
    const check = vi.spyOn(apiClient, "checkUpdate").mockReturnValue(new Promise((done) => { resolve = done; }));
    await click("设置");
    await click("检查更新");
    const button = container.querySelector<HTMLButtonElement>("button[aria-label='检查更新']");
    expect(button?.disabled).toBe(true);
    await act(async () => button!.click());
    expect(check).toHaveBeenCalledTimes(1);
    await act(async () => resolve({ current: "0.3.7", latest: "0.3.7", available: false, release_url: null, error: null }));
    expect(button?.disabled).toBe(false);
  });
});
