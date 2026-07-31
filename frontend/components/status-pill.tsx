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
  SCORE_AVAILABLE: "Có điểm model",
  TEXT_DETECTED: "Đã nhận diện",
  CHALLENGE_COMPLETE: "Đủ challenge",
  CHALLENGE_INCOMPLETE: "Thiếu challenge",
  CHALLENGE_MATCH: "Khớp challenge",
  CHALLENGE_MISMATCH: "Không khớp",
  SUSPICIOUS: "Có nghi vấn",
  NO_SUSPICIOUS_SIGNAL: "Chưa thấy nghi vấn",
  INCONCLUSIVE: "Chưa kết luận",
  UNAVAILABLE: "Không khả dụng",
  INVALID_MODEL_OUTPUT: "Output không hợp lệ",
  THRESHOLD_NOT_APPROVED: "Chưa có ngưỡng đánh giá",
};

export function StatusPill({ value }: { value: string }) {
  const tone = ["APPROVED", "COMPLETED", "CHALLENGE_COMPLETE", "CHALLENGE_MATCH", "NO_SUSPICIOUS_SIGNAL", "TEXT_DETECTED"].includes(value)
    ? "success"
    : ["REJECTED", "PROCESSING_FAILED", "SUSPICIOUS", "CHALLENGE_MISMATCH", "INVALID_MODEL_OUTPUT"].includes(value)
      ? "danger"
      : ["MANUAL_REVIEW", "CHALLENGE_INCOMPLETE", "INCONCLUSIVE", "UNAVAILABLE", "THRESHOLD_NOT_APPROVED"].includes(value)
        ? "warning"
        : "neutral";
  return <span className={`statusPill ${tone}`}>{LABELS[value] ?? value}</span>;
}
