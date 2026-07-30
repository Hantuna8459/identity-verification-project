"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, ChevronRight, ClipboardCheck, FileSearch, KeyRound, LayoutDashboard, LoaderCircle, LogOut, RefreshCw, Search, ShieldCheck, Users, X } from "lucide-react";
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
  evidence: Array<{ id: string; type: string; content_type: string; size_bytes: number; sha256: string }>;
};

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");


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
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể mở hồ sơ.");
    } finally {
      setBusy(false);
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
          <aside className="reviewDrawer" onClick={(event) => event.stopPropagation()}>
            <header><div><span>CHI TIẾT HỒ SƠ</span><h2>{detail.session.id.slice(0, 16)}…</h2></div><button onClick={() => setDetail(null)}><X /></button></header>
            <div className="drawerBody">
              <div className="detailGrid">
                <div><span>Loại giấy tờ</span><strong>{detail.session.document_type}</strong></div>
                <div><span>Trạng thái</span><StatusPill value={detail.session.stage} /></div>
                <div><span>Subject ref</span><code>{detail.session.subject_ref}</code></div>
                <div><span>Evidence</span><strong>{detail.evidence.length} tệp</strong></div>
              </div>
              <section className="reasonPanel"><span>Lý do chuyển kiểm duyệt</span>{detail.review.reason_codes.map((reason) => <strong key={reason}>{reason.replaceAll("_", " ")}</strong>)}</section>
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
