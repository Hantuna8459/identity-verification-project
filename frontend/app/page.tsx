"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import QRCode from "qrcode";
import { CheckCircle2, Copy, ExternalLink, Link2, LoaderCircle, MonitorUp, QrCode, RefreshCw, ShieldCheck, Smartphone } from "lucide-react";
import { Brand } from "@/components/brand";
import { StatusPill } from "@/components/status-pill";
import { api, SessionState, VID_CLIENT_KEY, WEB_CAPTURE_ENABLED } from "@/lib/api";

type CreatedSession = {
  session_id: string;
  session_token: string;
  stage: string;
  expires_at: string;
};

type Handoff = {
  handoff_id: string;
  handoff_token: string;
  capture_url: string;
  expires_at: string;
};

export default function HomePage() {
  const [subjectRef, setSubjectRef] = useState(() => `vid-${crypto.randomUUID().slice(0, 8)}`);
  const [session, setSession] = useState<CreatedSession | null>(null);
  const [handoff, setHandoff] = useState<Handoff | null>(null);
  const [state, setState] = useState<SessionState | null>(null);
  const [qrData, setQrData] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const expiresIn = `${Math.floor(remainingSeconds / 60)}:${String(remainingSeconds % 60).padStart(2, "0")}`;

  useEffect(() => {
    if (!handoff) return;
    QRCode.toDataURL(handoff.capture_url, {
      width: 320,
      margin: 2,
      color: { dark: "#151515", light: "#ffffff" },
      errorCorrectionLevel: "M",
    }).then(setQrData).catch(() => setError("Không thể tạo mã QR."));
  }, [handoff]);

  useEffect(() => {
    if (!handoff) return;
    const timer = window.setInterval(() => {
      setRemainingSeconds((value) => Math.max(0, value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [handoff]);

  useEffect(() => {
    if (!session) return;
    const readStatus = async () => {
      try {
        const next = await api<SessionState>(`/ekyc/sessions/${session.session_id}`, {
          headers: { "X-Session-Token": session.session_token },
        });
        setState(next);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Không thể đọc trạng thái phiên.");
      }
    };
    void readStatus();
    const timer = window.setInterval(readStatus, 3000);
    return () => window.clearInterval(timer);
  }, [session]);

  async function startSession() {
    setBusy(true);
    setError("");
    try {
      const created = await api<CreatedSession>("/ekyc/sessions", {
        method: "POST",
        headers: { "X-V-ID-Client-Key": VID_CLIENT_KEY },
        body: JSON.stringify({ subject_ref: subjectRef }),
      });
      setSession(created);
      const nextHandoff = await api<Handoff>(`/ekyc/sessions/${created.session_id}/handoffs`, {
        method: "POST",
        headers: { "X-Session-Token": created.session_token },
      });
      setHandoff(nextHandoff);
      setRemainingSeconds(Math.max(0, Math.floor((new Date(nextHandoff.expires_at).getTime() - new Date().getTime()) / 1000)));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể khởi tạo phiên eKYC.");
    } finally {
      setBusy(false);
    }
  }

  async function regenerateQr() {
    if (!session) return;
    setBusy(true);
    try {
      const next = await api<Handoff>(`/ekyc/sessions/${session.session_id}/handoffs`, {
        method: "POST",
        headers: { "X-Session-Token": session.session_token },
      });
      setHandoff(next);
      setRemainingSeconds(Math.max(0, Math.floor((new Date(next.expires_at).getTime() - new Date().getTime()) / 1000)));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tạo lại QR.");
    } finally {
      setBusy(false);
    }
  }

  async function copyLink() {
    if (!handoff) return;
    await navigator.clipboard.writeText(handoff.capture_url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <main className="desktopShell">
      <header className="topbar">
        <Brand />
        <div className="topbarActions">
          <span className="secureNote"><ShieldCheck size={16} /> Kết nối được bảo vệ</span>
          <Link className="textButton" href="/admin">Dành cho kiểm duyệt viên</Link>
        </div>
      </header>

      <section className="heroGrid">
        <div className="heroCopy">
          <span className="eyebrow">XÁC MINH DANH TÍNH V-ID</span>
          <h1>Một bước xác minh.<br /><em>Mở ra mọi kết nối.</em></h1>
          <p>Quét QR để tiếp tục trên điện thoại hoặc dùng camera trực tiếp trên thiết bị hiện tại trong chế độ demo.</p>
          <div className="trustRow">
            <span><CheckCircle2 size={18} /> Liên kết dùng một lần</span>
            <span><CheckCircle2 size={18} /> Dữ liệu được mã hóa</span>
          </div>
        </div>

        <div className="flowCard">
          {!session ? (
            <div className="startPanel">
              <div className="cardHeading">
                <div className="iconTile"><Smartphone size={23} /></div>
                <div><span>Bắt đầu</span><h2>Tạo phiên xác minh</h2></div>
              </div>
              <label className="fieldLabel">Mã tham chiếu V-ID
                <input value={subjectRef} onChange={(event) => setSubjectRef(event.target.value)} />
              </label>
              {error && <div className="errorBox">{error}</div>}
              <button className="primaryButton" disabled={busy || subjectRef.length < 3} onClick={startSession}>
                {busy ? <LoaderCircle className="spin" size={19} /> : <QrCode size={19} />}
                Tạo phiên eKYC
              </button>
              <p className="finePrint">Bằng cách tiếp tục, bạn xác nhận đang thực hiện quy trình xác minh danh tính.</p>
            </div>
          ) : (
            <div className="qrPanel">
              <div className="cardHeading split">
                <div><span>Bước tiếp theo</span><h2>Chọn cách tiếp tục</h2></div>
                <StatusPill value={state?.stage ?? session.stage} />
              </div>
              <p className="muted">Quét QR bằng điện thoại để mở phiên xác minh.</p>
              <div className="qrFrame">
                {qrData ? <Image src={qrData} width={256} height={256} unoptimized alt="QR mở phiên xác minh trên điện thoại" /> : <LoaderCircle className="spin" />}
                <span className="qrLogo">V</span>
              </div>
              <div className="expiry"><span></span>Mã hết hạn sau <strong>{expiresIn || "5:00"}</strong></div>
              <div className="buttonRow">
                <button className="secondaryButton" disabled={busy} onClick={regenerateQr}><RefreshCw size={17} /> Tạo lại</button>
                <button className="secondaryButton" onClick={copyLink}>{copied ? <CheckCircle2 size={17} /> : <Copy size={17} />} {copied ? "Đã sao chép" : "Sao chép link"}</button>
              </div>
              {WEB_CAPTURE_ENABLED && handoff && (
                <div className="webCaptureOption">
                  <div className="choiceDivider"><span>hoặc</span></div>
                  <a
                    className="webCaptureButton"
                    href={handoff.capture_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <span className="webCaptureIcon"><MonitorUp size={21} /></span>
                    <span>
                      <strong>eKYC bằng web</strong>
                      <small>Mở luồng xác minh trong tab mới</small>
                    </span>
                    <ExternalLink size={17} />
                  </a>
                  <p className="demoNote">Chế độ technical demo · Dùng cùng liên kết một lần với mã QR.</p>
                </div>
              )}
              {state?.stage === "COMPLETED" && (
                <div className="resultBox"><CheckCircle2 size={22} /><div><strong>Phiên đã hoàn tất</strong><span>Kết quả: {state.decision}</span></div></div>
              )}
              {error && <div className="errorBox">{error}</div>}
              <div className="sessionMeta"><Link2 size={15} /> Session <code>{session.session_id.slice(0, 12)}…</code></div>
            </div>
          )}
        </div>
      </section>

      <footer className="pageFooter"><span>© 2026 V-ID</span><span>Quyền riêng tư · Bảo mật · Trợ giúp</span></footer>
    </main>
  );
}
