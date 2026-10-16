import { Check, ExternalLink, LoaderCircle, TriangleAlert } from "lucide-react";

import type { UpdateStatus } from "../api/types";

interface UpdateBannerProps {
  status: UpdateStatus;
  version?: string | null;
  releaseUrl?: string | null;
  onDismiss?: () => void;
}

export function UpdateBanner({ status, version, releaseUrl, onDismiss }: UpdateBannerProps) {
  if (status === "idle") return null;

  const content = status === "checking"
    ? { icon: <LoaderCircle className="status-spin" size={15} />, text: "正在检查更新" }
    : status === "available"
      ? { icon: <ExternalLink size={15} />, text: `发现新版本${version ? ` v${version}` : ""}，请到发布页手动下载` }
      : status === "up_to_date"
        ? { icon: <Check size={15} />, text: "当前无需更新" }
        : { icon: <TriangleAlert size={15} />, text: "检查未完成，请稍后重试；不影响本地使用" };

  return (
    <div className={`update-banner update-banner-${status}`} role="status">
      <span className="update-banner-icon">{content.icon}</span>
      <span>{content.text}</span>
      {status === "available" && releaseUrl && (
        <a className="update-banner-action" href={releaseUrl} target="_blank" rel="noopener noreferrer">
          打开发布页
        </a>
      )}
      {onDismiss && status !== "checking" && (
        <button type="button" className="update-banner-dismiss" onClick={onDismiss} aria-label="关闭更新提示">
          关闭
        </button>
      )}
    </div>
  );
}
