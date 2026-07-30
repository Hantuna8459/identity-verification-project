"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Camera, Check, ChevronLeft, FileCheck2, LoaderCircle, LockKeyhole, ScanFace, ShieldCheck, Video } from "lucide-react";
import { Brand } from "@/components/brand";
import { api } from "@/lib/api";

type Claim = {
  session_id: string;
  capture_token: string;
  document_type: string;
  stage: string;
  expires_at: string;
};

function CaptureFlow() {
  const search = useSearchParams();
  const handoffToken = search.get("t") ?? "";
  const claimStarted = useRef(false);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [step, setStep] = useState(1);
  const [front, setFront] = useState<File | null>(null);
  const [back, setBack] = useState<File | null>(null);
  const [video, setVideo] = useState<File | null>(null);
  const [challenge, setChallenge] = useState("");
  const [busy, setBusy] = useState(Boolean(handoffToken));
  const [error, setError] = useState(handoffToken ? "" : "Liên kết QR không hợp lệ hoặc đã thiếu token.");

  useEffect(() => {
    if (!handoffToken || claimStarted.current) return;
    claimStarted.current = true;
    api<Claim>("/ekyc/handoffs/claim", {
      method: "POST",
      body: JSON.stringify({ token: handoffToken }),
    })
      .then(setClaim)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Không thể kết nối phiên."))
      .finally(() => setBusy(false));
  }, [handoffToken]);

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
    if (!claim || !front || (claim.document_type !== "PASSPORT_TD3" && !back)) return;
    setBusy(true);
    setError("");
    try {
      if (claim.document_type === "PASSPORT_TD3") {
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
      setError(reason instanceof Error ? reason.message : "Không thể tải giấy tờ.");
    } finally {
      setBusy(false);
    }
  }

  async function submitVideo() {
    if (!claim || !video) return;
    setBusy(true);
    setError("");
    try {
      await upload("SELFIE_VIDEO", video);
      await api("/ekyc/capture/submit", {
        method: "POST",
        headers: { Authorization: `Bearer ${claim.capture_token}` },
      });
      setStep(3);
    } catch (reason) {
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

  const isPassport = claim.document_type === "PASSPORT_TD3";

  return (
    <main className="mobileShell">
      <header className="mobileHeader"><Brand compact /><span><ShieldCheck size={15} /> Phiên an toàn</span></header>
      <div className="mobileProgress">
        {[1, 2, 3].map((item) => <i key={item} className={step >= item ? "active" : ""}></i>)}
      </div>

      {step === 1 && (
        <section className="mobileContent">
          <span className="stepLabel">BƯỚC 1 / 2</span>
          <h1>{isPassport ? "Chụp trang hộ chiếu" : "Chụp thẻ căn cước"}</h1>
          <p className="mobileLead">Đặt giấy tờ trên mặt phẳng, đủ sáng và không che các góc.</p>

          <label className={`captureTile ${front ? "selected" : ""}`}>
            <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(event) => setFront(event.target.files?.[0] ?? null)} />
            <span className="captureIcon">{front ? <FileCheck2 /> : <Camera />}</span>
            <span><strong>{isPassport ? "Trang thông tin cá nhân" : "Mặt trước"}</strong><small>{front?.name ?? "Chạm để mở camera"}</small></span>
            {front && <Check className="tileCheck" />}
          </label>

          {!isPassport && (
            <label className={`captureTile ${back ? "selected" : ""}`}>
              <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(event) => setBack(event.target.files?.[0] ?? null)} />
              <span className="captureIcon">{back ? <FileCheck2 /> : <Camera />}</span>
              <span><strong>Mặt sau</strong><small>{back?.name ?? "Chạm để mở camera"}</small></span>
              {back && <Check className="tileCheck" />}
            </label>
          )}

          <div className="captureTips"><ScanFace size={20} /><span>Giữ ảnh rõ nét, không lóa sáng và toàn bộ giấy tờ nằm trong khung.</span></div>
          {error && <div className="errorBox">{error}</div>}
          <button className="primaryButton mobileCta" disabled={busy || !front || (!isPassport && !back)} onClick={submitDocuments}>
            {busy ? <LoaderCircle className="spin" /> : "Tiếp tục"}
          </button>
        </section>
      )}

      {step === 2 && (
        <section className="mobileContent">
          <button className="backButton" onClick={() => setStep(1)}><ChevronLeft /> Quay lại</button>
          <span className="stepLabel">BƯỚC 2 / 2</span>
          <h1>Xác minh khuôn mặt</h1>
          <p className="mobileLead">Quay một video ngắn và đọc chậm dãy số hiển thị bên dưới.</p>

          <div className="challengeCard">
            <span>Đọc dãy số</span>
            <strong>{challenge}</strong>
            <small>Giữ khuôn mặt trong khung và nhìn thẳng vào camera</small>
          </div>

          <label className={`videoCapture ${video ? "selected" : ""}`}>
            <input type="file" accept="video/mp4,video/webm,video/quicktime" capture="user" onChange={(event) => setVideo(event.target.files?.[0] ?? null)} />
            <span>{video ? <FileCheck2 size={31} /> : <Video size={31} />}</span>
            <strong>{video ? "Video đã sẵn sàng" : "Quay video xác minh"}</strong>
            <small>{video?.name ?? "Thời lượng đề xuất 5–10 giây"}</small>
          </label>

          <div className="privacyLine"><LockKeyhole size={17} /> Video chỉ được dùng cho phiên xác minh này.</div>
          {error && <div className="errorBox">{error}</div>}
          <button className="primaryButton mobileCta" disabled={busy || !video} onClick={submitVideo}>
            {busy ? <LoaderCircle className="spin" /> : "Hoàn tất xác minh"}
          </button>
        </section>
      )}

      {step === 3 && (
        <section className="mobileCenter successState">
          <span className="successRing"><Check size={38} /></span>
          <span className="stepLabel">ĐÃ GỬI THÀNH CÔNG</span>
          <h1>Bạn đã hoàn tất</h1>
          <p>Hồ sơ đang được xử lý. Bạn có thể đóng trang này và theo dõi kết quả trên thiết bị ban đầu.</p>
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
