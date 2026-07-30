const LABELS: Record<string, string> = {
  AWAITING_MOBILE: "Chờ điện thoại",
  CAPTURING: "Đang thu thập",
  PROCESSING: "Đang xử lý",
  MANUAL_REVIEW: "Chờ kiểm duyệt",
  PROCESSING_FAILED: "Cần hỗ trợ",
  COMPLETED: "Hoàn tất",
  APPROVED: "Đã duyệt",
  REJECTED: "Từ chối",
  PENDING: "Chưa quyết định",
};

export function StatusPill({ value }: { value: string }) {
  const tone = value === "APPROVED" || value === "COMPLETED"
    ? "success"
    : value === "REJECTED" || value === "PROCESSING_FAILED"
      ? "danger"
      : value === "MANUAL_REVIEW"
        ? "warning"
        : "neutral";
  return <span className={`statusPill ${tone}`}>{LABELS[value] ?? value}</span>;
}
