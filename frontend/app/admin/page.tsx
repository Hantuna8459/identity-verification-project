"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, ChevronRight, ClipboardCheck, FileSearch, KeyRound, LayoutDashboard, LoaderCircle, LockKeyhole, LogOut, RefreshCw, ScanText, Search, ShieldCheck, Users, X } from "lucide-react";
import { Brand } from "@/components/brand";
import { StatusPill } from "@/components/status-pill";
import { api } from "@/lib/api";

type Review = {
  review_id: string;
  session_id: string;
  document_type: string;
  stage: string;
  decision: string;
  reason_codes: string[];
  created_at: string;
};

type Detail = {
  session: { id: string; subject_ref: string; document_type: string; stage: string; decision: string; created_at: string };
  review: { id: string; status: string; reason_codes: string[]; notes: string | null };
  analysis: Record<string, unknown> | null;
  demo_capabilities: { ocr_rerun: boolean };
  evidence: Array<{ id: string; type: string; content_type: string; size_bytes: number; sha256: string }>;
};

type OcrDocumentResult = {
  execution_status: string;
  engine?: string;
  lines: string[];
  mrz_validation?: { all_check_digits_valid?: boolean; mrz_detected?: boolean };
  reason_codes?: string[];
  error_type?: string;
};

type OcrRunResult = {
  schema_version: string;
  transient: true;
  documents: Record<string, OcrDocumentResult>;
};

const capabilityLabels: Record<string, string> = {
  ocr: "OCR giấy tờ",
  face_match: "Đối chiếu khuôn mặt",
  liveness: "Liveness thụ động",
  active_liveness: "Liveness chủ động",
  replay_attack: "Replay attack",
  camera_injection: "Camera injection",
  visual_deepfake: "Deepfake hình ảnh",
  voice_challenge: "Voice challenge",
  lip_sync: "Lip-sync",
};

const metricLabels: Record<string, string> = {
  cosine_similarity: "Độ tương đồng khuôn mặt",
  live_probability: "Xác suất live",
  manipulation_probability: "Xác suất can thiệp",
  similarity: "Độ khớp challenge",
  score: "Điểm rủi ro",
  value: "Ngưỡng",
  confidence: "Độ tin cậy",
  sampled_frames: "Frame đã lấy mẫu",
  frames_with_face: "Frame có khuôn mặt",
  matched_frames: "Frame dùng để đối chiếu",
  aggregation: "Cách tổng hợp face match",
  challenge_length: "Ký tự yêu cầu",
  recognized_digit_count: "Ký tự nhận diện",
  completed_step_count: "Bước hoàn thành",
  required_step_count: "Bước bắt buộc",
  sampled_pose_count: "Mẫu tư thế",
  duplicate_pairs: "Cặp frame trùng",
  sampled_frame_count: "Frame đã phân tích",
  approval_status: "Phạm vi ngưỡng",
  region_count: "Vùng giấy tờ",
  line_count: "Dòng OCR",
  mean_confidence: "Độ tin cậy OCR",
};

type ModelMetric = { key: string; label: string; value: string };
type CapabilitySummary = {
  executionStatus: string;
  reviewSignal: string;
  metrics: ModelMetric[];
  reasonCodes: string[];
  engine?: string;
};

type ProfileResultSummary = {
  totalCapabilities: number;
  completedCapabilities: number;
  attentionSignals: number;
  unavailableCapabilities: number;
};

function executionLabel(value: string): string {
  if (value === "COMPLETED") return "Model đã chạy xong";
  if (value === "INCONCLUSIVE") return "Dữ liệu chưa đủ để kết luận";
  if (value === "UNAVAILABLE") return "Model không khả dụng";
  return "Output không hợp lệ";
}

function formatMetric(key: string, value: unknown): ModelMetric {
  const label = metricLabels[key] ?? key.replaceAll("_", " ");
  let formatted = String(value ?? "Chưa cấu hình");
  if (typeof value === "number") formatted = value.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
  if (typeof value === "boolean") formatted = value ? "Có" : "Không";
  if (value === "NOT_APPROVED") formatted = "Chưa phê duyệt";
  if (value === "EVALUATION_ONLY") formatted = "Chỉ dùng demo";
  return { key, label, value: formatted };
}

function signalTone(value: string): string {
  if (["SUSPICIOUS", "CHALLENGE_MISMATCH", "INVALID_MODEL_OUTPUT"].includes(value)) return "danger";
  if (["CHALLENGE_INCOMPLETE", "INCONCLUSIVE", "UNAVAILABLE"].includes(value)) return "warning";
  if (["NO_SUSPICIOUS_SIGNAL", "CHALLENGE_MATCH", "CHALLENGE_COMPLETE", "TEXT_DETECTED"].includes(value)) return "success";
  return "neutral";
}

function capabilitySummary(value: unknown, capability: string): CapabilitySummary {
  if (!value || typeof value !== "object") return { executionStatus: "ERROR", reviewSignal: "INVALID_MODEL_OUTPUT", metrics: [], reasonCodes: ["INVALID_MODEL_OUTPUT"] };
  const record = value as Record<string, unknown>;
  const metrics: ModelMetric[] = [];
  function collect(child: unknown, parent = ""): void {
    if (!child || typeof child !== "object" || Array.isArray(child)) return;
    for (const [key, nested] of Object.entries(child)) {
      if (["status", "execution_status", "review_signal", "reason_codes", "engine", "score_direction", "warnings"].includes(key)) continue;
      if (nested && typeof nested === "object") collect(nested, key);
      else if (parent === "metrics" || parent === "details" || parent === "threshold" || key in metricLabels) metrics.push(formatMetric(key, nested));
    }
  }
  collect(record);
  const legacyStatuses: string[] = [];
  function collectLegacyStatuses(child: unknown): void {
    if (!child || typeof child !== "object" || Array.isArray(child)) return;
    for (const [key, nested] of Object.entries(child)) {
      if (key === "status" && typeof nested === "string") legacyStatuses.push(nested);
      else collectLegacyStatuses(nested);
    }
  }
  collectLegacyStatuses(record);
  const legacyStatus = typeof record.status === "string" ? record.status : legacyStatuses.includes("UNAVAILABLE") ? "UNAVAILABLE" : legacyStatuses.includes("INCONCLUSIVE") ? "INCONCLUSIVE" : legacyStatuses.length ? "OK" : undefined;
  const executionStatus = typeof record.execution_status === "string"
    ? record.execution_status
    : legacyStatus === "OK" ? "COMPLETED" : legacyStatus ?? "ERROR";
  let reviewSignal = typeof record.review_signal === "string" ? record.review_signal : "INCONCLUSIVE";
  if (typeof record.review_signal !== "string" && executionStatus === "COMPLETED") {
    if (record.suspicious === true || String(record.verdict ?? "").toLowerCase() === "fake") reviewSignal = "SUSPICIOUS";
    else if (["replay_attack", "camera_injection"].includes(capability)) reviewSignal = "NO_SUSPICIOUS_SIGNAL";
    else if (capability === "active_liveness") reviewSignal = record.sequence_complete === true ? "CHALLENGE_COMPLETE" : "CHALLENGE_INCOMPLETE";
    else if (capability === "voice_challenge") reviewSignal = Number(record.similarity) === 1 && Number(record.recognized_digit_count) === Number(record.challenge_length) ? "CHALLENGE_MATCH" : "CHALLENGE_MISMATCH";
    else if (capability === "ocr") reviewSignal = "TEXT_DETECTED";
    else reviewSignal = "SCORE_AVAILABLE";
  }
  const reasonCodes = Array.isArray(record.reason_codes)
    ? record.reason_codes.filter((reason): reason is string => typeof reason === "string")
    : [];
  const uniqueMetrics = [...new Map(metrics.map((metric) => [`${metric.label}:${metric.value}`, metric])).values()];
  if (reviewSignal === "SCORE_AVAILABLE") reviewSignal = "THRESHOLD_NOT_APPROVED";
  return {
    executionStatus,
    reviewSignal,
    metrics: uniqueMetrics,
    reasonCodes,
    engine: typeof record.engine === "string" ? record.engine : undefined,
  };
}

function profileResultSummary(analysis: Record<string, unknown> | null): ProfileResultSummary {
  const capabilities = analysis?.capabilities;
  if (!capabilities || typeof capabilities !== "object" || Array.isArray(capabilities)) {
    return { totalCapabilities: 0, completedCapabilities: 0, attentionSignals: 0, unavailableCapabilities: 0 };
  }

  const summaries = Object.entries(capabilities as Record<string, unknown>)
    .filter(([capability]) => capability !== "ocr")
    .map(([capability, value]) => capabilitySummary(value, capability));
  const attentionSignals = new Set([
    "SUSPICIOUS",
    "CHALLENGE_MISMATCH",
    "CHALLENGE_INCOMPLETE",
    "INCONCLUSIVE",
    "INVALID_MODEL_OUTPUT",
    "THRESHOLD_NOT_APPROVED",
  ]);

  return {
    totalCapabilities: summaries.length,
    completedCapabilities: summaries.filter((summary) => summary.executionStatus === "COMPLETED").length,
    attentionSignals: summaries.filter((summary) => attentionSignals.has(summary.reviewSignal)).length,
    unavailableCapabilities: summaries.filter((summary) => summary.executionStatus === "UNAVAILABLE").length,
  };
}

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [ocrResult, setOcrResult] = useState<OcrRunResult | null>(null);
  const [ocrBusy, setOcrBusy] = useState(false);
  const [ocrError, setOcrError] = useState("");


  async function loadReviews(authToken = token) {
    setBusy(true);
    setError("");
    try {
      const data = await api<Review[]>("/reviews?status=OPEN", {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      setReviews(data);
      setAuthenticated(true);
      window.sessionStorage.setItem("vid-reviewer-token", authToken);
    } catch (reason) {
      setAuthenticated(false);
      setError(reason instanceof Error ? reason.message : "Không thể đăng nhập.");
    } finally {
      setBusy(false);
    }
  }

  async function openReview(sessionId: string) {
    setBusy(true);
    try {
      const data = await api<Detail>(`/reviews/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setDetail(data);
      setNotes("");
      setOcrResult(null);
      setOcrError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể mở hồ sơ.");
    } finally {
      setBusy(false);
    }
  }

  async function runOcr() {
    if (!detail) return;
    setOcrBusy(true);
    setOcrError("");
    try {
      const result = await api<OcrRunResult>(`/reviews/${detail.session.id}/ocr-runs`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      setOcrResult(result);
    } catch (reason) {
      setOcrError(reason instanceof Error ? reason.message : "Không thể chạy OCR.");
    } finally {
      setOcrBusy(false);
    }
  }

  async function decide(decision: "APPROVED" | "REJECTED") {
    if (!detail || notes.trim().length < 3) return;
    setBusy(true);
    try {
      await api(`/reviews/${detail.session.id}/decisions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({ decision, notes }),
      });
      setDetail(null);
      await loadReviews();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể ghi quyết định.");
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    window.sessionStorage.removeItem("vid-reviewer-token");
    setAuthenticated(false);
    setToken("");
    setReviews([]);
    setDetail(null);
    setOcrResult(null);
  }

  if (!authenticated) {
    return (
      <main className="adminLogin">
        <Link href="/"><Brand /></Link>
        <section className="loginCard">
          <span className="adminBadge"><ShieldCheck size={18} /> Khu vực được bảo vệ</span>
          <h1>Đăng nhập kiểm duyệt</h1>
          <p>Nhập reviewer token được cấp cho môi trường hiện tại.</p>
          <label className="fieldLabel">Reviewer token
            <div className="inputWithIcon"><KeyRound size={18} /><input type="password" value={token} onChange={(event) => setToken(event.target.value)} placeholder="••••••••••••" /></div>
          </label>
          {error && <div className="errorBox">{error}</div>}
          <button className="primaryButton" disabled={busy || !token} onClick={() => loadReviews()}>{busy ? <LoaderCircle className="spin" /> : "Đăng nhập"}</button>
          <small>Development mặc định: <code>local-reviewer-token</code></small>
        </section>
      </main>
    );
  }

  const filtered = reviews.filter((review) => review.session_id.includes(query) || review.document_type.toLowerCase().includes(query.toLowerCase()));
  const profileResult = detail ? profileResultSummary(detail.analysis) : null;

  return (
    <main className="adminShell">
      <aside className="adminSidebar">
        <Brand />
        <nav>
          <button><LayoutDashboard /> Tổng quan</button>
          <button className="active"><ClipboardCheck /> Hồ sơ eKYC <b>{reviews.length}</b></button>
          <button><Users /> Người kiểm duyệt</button>
          <button><FileSearch /> Nhật ký audit</button>
        </nav>
        <button className="logoutButton" onClick={logout}><LogOut /> Đăng xuất</button>
      </aside>

      <section className="adminMain">
        <header className="adminTopbar">
          <div><span>V-ID OPERATIONS</span><h1>Kiểm duyệt eKYC</h1></div>
          <div className="reviewerChip"><i>RV</i><span><strong>Kiểm duyệt viên</strong><small>Phiên development</small></span></div>
        </header>

        <div className="metricGrid">
          <article><span>Chờ kiểm duyệt</span><strong>{reviews.length}</strong><small>Cần xử lý</small></article>
          <article><span>Đang xử lý</span><strong>0</strong><small>Pipeline offline</small></article>
          <article><span>Hoàn tất hôm nay</span><strong>—</strong><small>Theo audit log</small></article>
        </div>

        <section className="tableCard">
          <div className="tableTools">
            <div><h2>Hàng đợi kiểm duyệt</h2><p>Hồ sơ không đủ điều kiện quyết định tự động</p></div>
            <div className="toolActions"><label className="searchBox"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm mã phiên…" /></label><button className="iconButton" onClick={() => loadReviews()}><RefreshCw /></button></div>
          </div>
          <div className="reviewTable">
            <div className="tableHeader"><span>Mã phiên</span><span>Giấy tờ</span><span>Lý do</span><span>Trạng thái</span><span></span></div>
            {filtered.length === 0 ? (
              <div className="emptyQueue"><ClipboardCheck /><strong>Không có hồ sơ đang chờ</strong><span>Hàng đợi sẽ tự cập nhật khi có phiên mới.</span></div>
            ) : filtered.map((review) => (
              <button className="tableRow" key={review.review_id} onClick={() => openReview(review.session_id)}>
                <span><strong>{review.session_id.slice(0, 12)}…</strong><small>{new Date(review.created_at).toLocaleString("vi-VN")}</small></span>
                <span>{review.document_type}</span>
                <span>{review.reason_codes[0]?.replaceAll("_", " ")}</span>
                <span><StatusPill value={review.stage} /></span>
                <ChevronRight />
              </button>
            ))}
          </div>
        </section>
      </section>

      {detail && (
        <div className="drawerBackdrop" onClick={() => setDetail(null)}>
          <aside className="reviewDrawer" role="dialog" aria-modal="true" aria-label="Chi tiết hồ sơ eKYC" onClick={(event) => event.stopPropagation()}>
            <header><div><span>CHI TIẾT HỒ SƠ</span><h2>{detail.session.id.slice(0, 16)}…</h2></div><button onClick={() => setDetail(null)}><X /></button></header>
            <div className="drawerBody">
              <div className="detailGrid">
                <div><span>Loại giấy tờ</span><strong>{detail.session.document_type}</strong></div>
                <div><span>Trạng thái</span><StatusPill value={detail.session.stage} /></div>
                <div><span>Subject ref</span><code>{detail.session.subject_ref}</code></div>
                <div><span>Evidence</span><strong>{detail.evidence.length} tệp</strong></div>
              </div>
              <section className="profileResult">
                <div className="profileResultHeader">
                  <div><span className="sectionEyebrow">KẾT QUẢ HỒ SƠ</span><h3>Tổng hợp trước kiểm duyệt</h3></div>
                  <StatusPill value={detail.session.decision} />
                </div>
                <p>Hồ sơ technical demo đang chờ quyết định của kiểm duyệt viên. Các tín hiệu model bên dưới không tự động phê duyệt hoặc từ chối.</p>
                <div className="profileResultGrid">
                  <div><span>Model đã chạy</span><strong>{profileResult?.completedCapabilities ?? 0}/{profileResult?.totalCapabilities ?? 0}</strong></div>
                  <div><span>Tín hiệu cần xem</span><strong>{profileResult?.attentionSignals ?? 0}</strong></div>
                  <div><span>Model không khả dụng</span><strong>{profileResult?.unavailableCapabilities ?? 0}</strong></div>
                  <div><span>Trạng thái review</span><strong>{detail.review.status === "OPEN" ? "Đang mở" : "Đã xử lý"}</strong></div>
                </div>
              </section>
              <section className="reasonPanel"><span>Lý do chuyển kiểm duyệt</span>{detail.review.reason_codes.map((reason) => <strong key={reason}>{reason.replaceAll("_", " ")}</strong>)}</section>
              {detail.demo_capabilities.ocr_rerun && (
                <section className="ocrDisclosure">
                  <div className="ocrDisclosureHeader">
                    <div><span className="sectionEyebrow">TECHNICAL DEMO</span><h3>Kết quả OCR được bảo vệ</h3><p>Evidence chỉ được giải mã trong memory khi reviewer chủ động chạy OCR. Kết quả không được lưu lại.</p></div>
                    <LockKeyhole />
                  </div>
                  {!ocrResult ? (
                    <div className="ocrProtectedState">
                      <div><LockKeyhole /><span><strong>Chưa giải mã evidence</strong><small>Thao tác này chỉ chạy OCR giấy tờ, không chạy các model sinh trắc học.</small></span></div>
                      <button className="primaryButton ocrRunButton" disabled={ocrBusy} onClick={runOcr}>{ocrBusy ? <LoaderCircle className="spin" /> : <ScanText />} {ocrBusy ? "Đang chạy OCR…" : "Chạy OCR để xem kết quả"}</button>
                    </div>
                  ) : (
                    <div className="ocrDocumentGrid">
                      {Object.entries(ocrResult.documents).map(([document, result]) => (
                        <article key={document}>
                          <header><div><span>{document.replaceAll("_", " ")}</span><small>{result.engine ?? "OCR engine không khả dụng"}</small></div><StatusPill value={result.execution_status} /></header>
                          {result.lines.length > 0 ? <ol>{result.lines.map((line, index) => <li key={`${document}:${index}`}>{line}</li>)}</ol> : <p>Không có nội dung OCR để hiển thị.</p>}
                          {result.mrz_validation && <div className="mrzValidation"><span>MRZ</span><strong>{result.mrz_validation.all_check_digits_valid ? "Check digit hợp lệ" : result.mrz_validation.mrz_detected ? "Check digit cần kiểm tra" : "Không phát hiện MRZ TD3"}</strong></div>}
                          {(result.reason_codes?.length || result.error_type) && <small className="ocrErrorMeta">{result.reason_codes?.join(" · ") || result.error_type}</small>}
                        </article>
                      ))}
                      <button className="secondaryButton ocrRerunButton" disabled={ocrBusy} onClick={runOcr}><RefreshCw /> Chạy lại OCR</button>
                    </div>
                  )}
                  {ocrError && <div className="errorBox">{ocrError}</div>}
                  <small className="ocrDemoWarning">Chỉ dùng để quan sát định tính trong technical demo; không phải benchmark độ chính xác.</small>
                </section>
              )}
              {Boolean(detail.analysis?.capabilities) && (
                <section className="modelOutput">
                  <div className="modelOutputHeader">
                    <div><span className="sectionEyebrow">PHÂN TÍCH TỰ ĐỘNG</span><h3>Kết quả các mô hình</h3><p>Tín hiệu hỗ trợ kiểm duyệt, không phải quyết định tự động.</p></div>
                    <span>{String(detail.analysis?.schema_version ?? "offline demo")}</span>
                  </div>
                  <div className="modelLegend"><span><i className="legendSignal" />Tín hiệu cần xem</span><span><i className="legendExecution" />Trạng thái xử lý</span></div>
                  <div className="modelOutputGrid">
                    {Object.entries((detail.analysis?.capabilities ?? {}) as Record<string, unknown>).filter(([key]) => key !== "ocr").map(([key, value]) => {
                      const summary = capabilitySummary(value, key);
                      return (
                        <article className={`modelOutputCard ${signalTone(summary.reviewSignal)}`} key={key}>
                          <div className="modelOutputCardTitle">
                            <div><strong>{capabilityLabels[key] ?? key}</strong><span>{executionLabel(summary.executionStatus)}</span></div>
                            <StatusPill value={summary.reviewSignal} />
                          </div>
                          {summary.reviewSignal === "THRESHOLD_NOT_APPROVED" && <p className="modelInterpretation">Chưa có ngưỡng được benchmark và phê duyệt để kết luận điểm này là tốt hay xấu.</p>}
                          {summary.metrics.length > 0 && (
                            <details className="modelTechnicalDetails">
                              <summary>Chi tiết kỹ thuật</summary>
                              <div className="modelMetrics">
                                {summary.metrics.map((metric) => <div key={`${metric.key}:${metric.value}`}><span>{metric.label}</span><strong>{metric.value}</strong></div>)}
                              </div>
                            </details>
                          )}
                          {(summary.reasonCodes.length > 0 || summary.engine) && (
                            <div className="modelCardMeta">
                              {summary.reasonCodes.length > 0 && <div>{summary.reasonCodes.map((reason) => <span key={reason}>{reason.replaceAll("_", " ")}</span>)}</div>}
                              {summary.engine && <small title={summary.engine}>Engine: {summary.engine}</small>}
                            </div>
                          )}
                        </article>
                      );
                    })}
                  </div>
                </section>
              )}
              <section className="evidenceList"><h3>Evidence metadata</h3>{detail.evidence.map((item) => <div key={item.id}><FileSearch /><span><strong>{item.type}</strong><small>{item.content_type} · {(item.size_bytes / 1024).toFixed(1)} KB</small></span><code>{item.sha256.slice(0, 10)}…</code></div>)}</section>
              <label className="fieldLabel">Ghi chú bắt buộc<textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Ghi rõ căn cứ cho quyết định…" rows={4} /></label>
              {error && <div className="errorBox">{error}</div>}
            </div>
            <footer><button className="rejectButton" disabled={busy || notes.trim().length < 3} onClick={() => decide("REJECTED")}><X /> Từ chối</button><button className="approveButton" disabled={busy || notes.trim().length < 3} onClick={() => decide("APPROVED")}><Check /> Phê duyệt</button></footer>
          </aside>
        </div>
      )}
    </main>
  );
}
