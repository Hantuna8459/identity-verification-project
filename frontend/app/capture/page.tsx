"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BookOpen, Check, CreditCard, FileCheck2, LoaderCircle, Upload, LockKeyhole, ScanFace, ShieldCheck } from "lucide-react";
import { Brand } from "@/components/brand";
import { ChallengeRecorder, DocumentCamera } from "@/components/camera-capture";
import { api } from "@/lib/api";

type Claim = {
  session_id: string;
  capture_token: string;
  document_type: string | null;
  stage: string;
  expires_at: string;
};

type CaptureDocumentType = "CCCD" | "PASSPORT";
type DocumentSide = "front" | "back";
type SubmissionState = "idle" | "submitting" | "submitted" | "failed";

function captureDocumentType(value: string | null): CaptureDocumentType | null {
  if (value === "PASSPORT_TD3") return "PASSPORT";
  if (value === "CCCD" || value === "CCCD_2021" || value === "CAN_CUOC_2024") return "CCCD";
  return null;
}

function CaptureFlow() {
  const search = useSearchParams();
  const handoffToken = search.get("t") ?? "";
  const claimStarted = useRef(false);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [step, setStep] = useState(1);
  const [documentType, setDocumentType] = useState<CaptureDocumentType | null>(null);
  const [activeSide, setActiveSide] = useState<DocumentSide>("front");
  const [front, setFront] = useState<File | null>(null);
  const [back, setBack] = useState<File | null>(null);
  const [recording, setRecording] = useState<File | null>(null);
  const [challenge, setChallenge] = useState("");
  const [submissionState, setSubmissionState] = useState<SubmissionState>("idle");
  const [busy, setBusy] = useState(Boolean(handoffToken));
  const [error, setError] = useState(handoffToken ? "" : "Liên kết QR không hợp lệ hoặc đã thiếu token.");

  useEffect(() => {
    if (!handoffToken || claimStarted.current) return;
    claimStarted.current = true;
    api<Claim>("/ekyc/handoffs/claim", {
      method: "POST",
      body: JSON.stringify({ token: handoffToken }),
    })
      .then((nextClaim) => {
        setClaim(nextClaim);
        setDocumentType(captureDocumentType(nextClaim.document_type));
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Không thể kết nối phiên."))
      .finally(() => setBusy(false));
  }, [handoffToken]);

  function chooseDocumentType(nextType: CaptureDocumentType) {
    if (nextType !== documentType) {
      setFront(null);
      setBack(null);
      setActiveSide("front");
    }
    setDocumentType(nextType);
    setError("");
  }

  function receiveUploadedDocument(side: DocumentSide, file: File | null) {
    if (!file) return;
    if (side === "front") setFront(file);
    else setBack(file);
    setError("");
  }

  function receiveDocumentPhoto(file: File) {
    if (activeSide === "front") {
      setFront(file);
      if (documentType === "CCCD") setActiveSide("back");
    } else {
      setBack(file);
    }
    setError("");
  }

  async function upload(kind: string, file: File) {
    if (!claim) return;
    const form = new FormData();
    form.append("file", file);
    await api(`/ekyc/capture/evidence/${kind}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${claim.capture_token}` },
      body: form,
    });
  }

  async function submitDocuments() {
    const isPassport = documentType === "PASSPORT";
    if (!claim || !documentType || !front || (!isPassport && !back)) return;
    setBusy(true);
    setError("");
    try {
      const selected = await api<{ document_type: string }>("/ekyc/capture/document-type", {
        method: "POST",
        headers: { Authorization: `Bearer ${claim.capture_token}` },
        body: JSON.stringify({ document_type: documentType }),
      });
      setClaim({ ...claim, document_type: selected.document_type });
      if (isPassport) {
        await upload("PASSPORT_PAGE", front);
      } else {
        await upload("DOCUMENT_FRONT", front);
        await upload("DOCUMENT_BACK", back as File);
      }
      const next = await api<{ challenge: string }>("/ekyc/capture/voice-challenge", {
        method: "POST",
        headers: { Authorization: `Bearer ${claim.capture_token}` },
      });
      setChallenge(next.challenge);
      setStep(2);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể gửi ảnh giấy tờ.");
    } finally {
      setBusy(false);
    }
  }

  async function submitChallenge() {
    if (!claim || !recording) return;
    setStep(3);
    setSubmissionState("submitting");
    setBusy(true);
    setError("");
    try {
      await upload("SELFIE_VIDEO", recording);
      await api("/ekyc/capture/submit", {
        method: "POST",
        headers: { Authorization: `Bearer ${claim.capture_token}` },
      });
      setSubmissionState("submitted");
    } catch (reason) {
      setSubmissionState("failed");
      setError(reason instanceof Error ? reason.message : "Không thể hoàn tất phiên.");
    } finally {
      setBusy(false);
    }
  }

  if (busy && !claim) {
    return <div className="mobileCenter"><LoaderCircle className="spin" size={34} /><p>Đang kết nối phiên an toàn…</p></div>;
  }

  if (!claim) {
    return <div className="mobileCenter errorState"><LockKeyhole size={34} /><h1>Không thể mở phiên</h1><p>{error}</p></div>;
  }

  const isPassport = documentType === "PASSPORT";
  const targetLabel = isPassport ? "Trang thông tin" : activeSide === "front" ? "Mặt trước" : "Mặt sau";
  const documentsReady = Boolean(front && (isPassport || back));

  return (
    <main className="mobileShell captureShell">
      <header className="mobileHeader"><Brand compact /><span><ShieldCheck size={15} /> Phiên an toàn</span></header>
      <div className="mobileProgress">
        {[1, 2, 3].map((item) => <i key={item} className={step >= item ? "active" : ""} />)}
      </div>

      {step === 1 && (
        <section className="mobileContent captureContent">
          <span className="stepLabel">BƯỚC 1 / 2</span>
          <h1>Chụp giấy tờ</h1>
          <p className="mobileLead">Chọn loại giấy tờ bạn đang có. Với CCCD, bạn có thể tải ảnh lên hoặc chụp trực tiếp bằng camera.</p>

          <div className="documentChoiceGrid" role="radiogroup" aria-label="Loại giấy tờ">
            <button type="button" role="radio" aria-checked={documentType === "CCCD"} className={documentType === "CCCD" ? "selected" : ""} onClick={() => chooseDocumentType("CCCD")}>
              <span><CreditCard /></span><strong>CCCD</strong><small>Chụp mặt trước và mặt sau</small>{documentType === "CCCD" && <Check />}
            </button>
            <button type="button" role="radio" aria-checked={documentType === "PASSPORT"} className={documentType === "PASSPORT" ? "selected" : ""} onClick={() => chooseDocumentType("PASSPORT")}>
              <span><BookOpen /></span><strong>Hộ chiếu</strong><small>Chụp trang thông tin cá nhân</small>{documentType === "PASSPORT" && <Check />}
            </button>
          </div>

          {documentType && (
            <>
              <div className="captureSideTabs" aria-label="Phần giấy tờ cần chụp">
                <button type="button" className={activeSide === "front" ? "active" : ""} onClick={() => setActiveSide("front")}>
                  {front && <FileCheck2 size={15} />} {isPassport ? "Trang thông tin" : "Mặt trước"}
                </button>
                {!isPassport && <button type="button" className={activeSide === "back" ? "active" : ""} onClick={() => setActiveSide("back")}>{back && <FileCheck2 size={15} />} Mặt sau</button>}
              </div>
              {!isPassport && (
                <div className="documentUploadOption">
                  <div className="captureOptionDivider"><span>Tải ảnh CCCD có sẵn</span></div>
                  <div className="documentUploadGrid">
                    <label className={front ? "selected" : ""}>
                      <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => receiveUploadedDocument("front", event.target.files?.[0] ?? null)} />
                      {front ? <FileCheck2 /> : <Upload />}
                      <span><strong>Mặt trước</strong><small>{front?.name ?? "Chọn ảnh từ thiết bị"}</small></span>
                    </label>
                    <label className={back ? "selected" : ""}>
                      <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => receiveUploadedDocument("back", event.target.files?.[0] ?? null)} />
                      {back ? <FileCheck2 /> : <Upload />}
                      <span><strong>Mặt sau</strong><small>{back?.name ?? "Chọn ảnh từ thiết bị"}</small></span>
                    </label>
                  </div>
                  <div className="captureOptionDivider"><span>Hoặc chụp trực tiếp</span></div>
                </div>
              )}
              <DocumentCamera targetLabel={targetLabel} onCapture={receiveDocumentPhoto} onError={setError} />
              <div className="captureTips"><ScanFace size={20} /><span>Đưa đủ bốn góc giấy tờ vào khung, giữ camera ổn định và tránh ánh sáng phản chiếu.</span></div>
            </>
          )}

          {error && <div className="errorBox" role="alert">{error}</div>}
          <button className="primaryButton mobileCta" disabled={busy || !documentsReady} onClick={submitDocuments}>
            {busy ? <LoaderCircle className="spin" /> : "Tiếp tục xác minh khuôn mặt"}
          </button>
        </section>
      )}

      {step === 2 && (
        <section className="mobileContent captureContent">
          <span className="stepLabel">BƯỚC 2 / 2</span>
          <h1>Challenge khuôn mặt</h1>
          <p className="mobileLead">Làm lần lượt từng hướng dẫn. Chỉ quay nhẹ một lần mỗi bên; dãy số chỉ xuất hiện sau khi bạn đã nhìn thẳng trở lại.</p>

          <ChallengeRecorder challenge={challenge} onRecorded={setRecording} onError={setError} />
          <div className="privacyLine"><LockKeyhole size={17} /> Không thể chọn video có sẵn; camera được ghi trực tiếp cho phiên này.</div>
          {error && <div className="errorBox" role="alert">{error}</div>}
          <button className="primaryButton mobileCta" disabled={busy || !recording} onClick={submitChallenge}>
            Tiếp tục
          </button>
        </section>
      )}

      {step === 3 && (
        <section className={`mobileCenter processingState ${submissionState}`}>
          {submissionState === "submitting" && (
            <>
              <span className="processingRing"><LoaderCircle className="spin" size={38} /></span>
              <span className="stepLabel">ĐANG GỬI HỒ SƠ</span>
              <h1>Đã hoàn tất challenge</h1>
              <p>Bạn đã sang bước tiếp theo. Hệ thống đang tải evidence và xử lý ở nền; vui lòng giữ trang này mở.</p>
            </>
          )}
          {submissionState === "submitted" && (
            <>
              <span className="successRing"><Check size={38} /></span>
              <span className="stepLabel">ĐÃ GỬI THÀNH CÔNG</span>
              <h1>Đã gửi để kiểm tra</h1>
              <p>Hồ sơ đã chuyển tới kiểm duyệt thủ công. Trạng thái này không đồng nghĩa challenge đã đạt; bạn có thể đóng trang này.</p>
            </>
          )}
          {submissionState === "failed" && (
            <>
              <span className="errorRing"><LockKeyhole size={34} /></span>
              <span className="stepLabel">CHƯA GỬI ĐƯỢC</span>
              <h1>Cần thử gửi lại</h1>
              <p>{error}</p>
              <button className="primaryButton retrySubmitButton" disabled={busy} onClick={submitChallenge}>
                {busy ? <LoaderCircle className="spin" /> : "Thử gửi lại"}
              </button>
            </>
          )}
          <div className="referenceBox"><span>Mã phiên</span><code>{claim.session_id.slice(0, 18)}…</code></div>
        </section>
      )}

      <footer className="mobileFooter"><LockKeyhole size={14} /> Dữ liệu được mã hóa trong suốt quá trình</footer>
    </main>
  );
}

export default function CapturePage() {
  return <Suspense fallback={<div className="mobileCenter"><LoaderCircle className="spin" /></div>}><CaptureFlow /></Suspense>;
}
