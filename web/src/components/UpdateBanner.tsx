import { Check, Download, LoaderCircle, TriangleAlert } from "lucide-react";

import type { UpdateStatus } from "../api/types";

interface UpdateBannerProps {
  status: UpdateStatus;
  version?: string;
  onApply?: () => void;
  onDismiss?: () => void;
}

export function UpdateBanner({ status, version, onApply, onDismiss }: UpdateBannerProps) {
  if (status === "idle") return null;

  const content = status === "checking"
    ? { icon: <LoaderCircle className="status-spin" size={15} />, text: "正在检查更新" }
    : status === "available"
      ? { icon: <Download size={15} />, text: version ? `发现版本 ${version}` : "发现新版本" }
      : status === "downloading"
        ? { icon: <LoaderCircle className="status-spin" size={15} />, text: "正在准备更新" }
        : status === "applying"
          ? { icon: <LoaderCircle className="status-spin" size={15} />, text: "正在应用更新" }
          : status === "succeeded"
            ? { icon: <Check size={15} />, text: "更新已完成" }
            : status === "rollback"
              ? { icon: <TriangleAlert size={15} />, text: "更新失败，已回滚" }
      : status === "up_to_date"
        ? { icon: <Check size={15} />, text: "已是最新版本" }
        : { icon: <TriangleAlert size={15} />, text: "更新检查失败" };

  return (
    <div className={`update-banner update-banner-${status}`} role="status">
      <span className="update-banner-icon">{content.icon}</span>
      <span>{content.text}</span>
      {status === "available" && onApply && (
        <button type="button" className="update-banner-action" onClick={onApply}>
          准备更新
        </button>
      )}
      {onDismiss && status !== "checking" && (
        <button type="button" className="update-banner-dismiss" onClick={onDismiss} aria-label="关闭更新提示">
          关闭
        </button>
      )}
    </div>
  );
}
