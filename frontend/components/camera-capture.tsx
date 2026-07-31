"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Check, LoaderCircle, RefreshCw, Square, Video } from "lucide-react";

type CameraState = "idle" | "requesting" | "ready" | "recording" | "recorded";

function stopStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => track.stop());
}

function cameraErrorMessage(reason: unknown) {
  if (reason instanceof DOMException && reason.name === "NotAllowedError") {
    return "Bạn cần cho phép truy cập camera và microphone để tiếp tục.";
  }
  if (reason instanceof DOMException && reason.name === "NotFoundError") {
    return "Không tìm thấy camera phù hợp trên thiết bị này.";
  }
  return reason instanceof Error ? reason.message : "Không thể mở camera.";
}

function supportedRecorderMimeType() {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = [
    "video/webm;codecs=vp8,opus",
    "video/webm",
    "video/mp4;codecs=h264,aac",
    "video/mp4",
  ];
  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) ?? "";
}

type DocumentCameraProps = {
  targetLabel: string;
  onCapture: (file: File) => void;
  onError: (message: string) => void;
};

export function DocumentCamera({ targetLabel, onCapture, onError }: DocumentCameraProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>("idle");

  useEffect(() => () => stopStream(streamRef.current), []);

  async function startCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      onError("Trình duyệt này không hỗ trợ camera trực tiếp. Hãy thử Chrome, Edge hoặc Safari mới hơn.");
      return;
    }
    setState("requesting");
    onError("");
    try {
      stopStream(streamRef.current);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setState("ready");
    } catch (reason) {
      setState("idle");
      onError(cameraErrorMessage(reason));
    }
  }

  function captureFrame() {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) {
      onError("Camera chưa sẵn sàng. Vui lòng thử lại.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      onError("Không thể tạo ảnh từ camera.");
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          onError("Không thể tạo ảnh từ camera.");
          return;
        }
        onCapture(new File([blob], `document-${Date.now()}.jpg`, { type: "image/jpeg" }));
      },
      "image/jpeg",
      0.92,
    );
  }

  return (
    <div className="cameraPanel documentCamera">
      <div className="cameraViewport">
        <video ref={videoRef} autoPlay muted playsInline aria-label="Camera chụp giấy tờ" />
        {state === "ready" && (
          <>
            <div className="documentGuide" aria-hidden="true" />
            <div className="cameraHint">Đặt {targetLabel.toLowerCase()} vừa khung · tránh lóa sáng</div>
          </>
        )}
        {state === "idle" && (
          <div className="cameraPlaceholder"><Camera size={34} /><strong>Camera chưa bật</strong><span>Giấy tờ được chụp trực tiếp, không chọn ảnh có sẵn.</span></div>
        )}
        {state === "requesting" && <div className="cameraPlaceholder"><LoaderCircle className="spin" /><span>Đang mở camera…</span></div>}
      </div>
      <div className="cameraToolbar">
        {state !== "ready" ? (
          <button type="button" className="primaryButton" disabled={state === "requesting"} onClick={startCamera}>
            <Camera size={18} /> Bật camera
          </button>
        ) : (
          <>
            <button type="button" className="secondaryButton compactButton" onClick={startCamera}><RefreshCw size={16} /> Mở lại</button>
            <button type="button" className="primaryButton compactButton" onClick={captureFrame}><Camera size={18} /> Chụp {targetLabel.toLowerCase()}</button>
          </>
        )}
      </div>
    </div>
  );
}


type ChallengeRecorderProps = {
  challenge: string;
  onRecorded: (file: File | null) => void;
  onError: (message: string) => void;
};

type GuidedChallengeStep = {
  label: string;
  detail: string;
  action: string;
  showChallenge?: boolean;
};

const guidedChallengeSteps: GuidedChallengeStep[] = [
  {
    label: "Nhìn thẳng vào camera",
    detail: "Giữ khuôn mặt ở giữa khung trước khi bắt đầu.",
    action: "Tôi đã sẵn sàng",
  },
  {
    label: "Quay nhẹ sang trái",
    detail: "Chỉ cần quay nhẹ một lần, không cần giữ quá lâu.",
    action: "Đã quay trái",
  },
  {
    label: "Trở lại nhìn thẳng",
    detail: "Đưa khuôn mặt về giữa khung rồi mới tiếp tục.",
    action: "Đã nhìn thẳng",
  },
  {
    label: "Quay nhẹ sang phải",
    detail: "Chỉ cần quay nhẹ một lần, không cần giữ quá lâu.",
    action: "Đã quay phải",
  },
  {
    label: "Trở lại nhìn thẳng",
    detail: "Giữ khuôn mặt ở giữa khung để chuẩn bị đọc số.",
    action: "Đã trở về giữa",
  },
  {
    label: "Đọc rõ dãy số",
    detail: "Đọc tự nhiên từng số, sau đó xác nhận hoàn tất.",
    action: "Tôi đã đọc xong",
    showChallenge: true,
  },
];

const minimumStepHoldMs = 1100;
const hiddenCaptureTimeoutMs = 75_000;

export function ChallengeRecorder({ challenge, onRecorded, onError }: ChallengeRecorderProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const discardRecordingRef = useRef(false);
  const stepDelayRef = useRef<number | null>(null);
  const captureTimeoutRef = useRef<number | null>(null);
  const [state, setState] = useState<CameraState>("idle");
  const [stepIndex, setStepIndex] = useState(0);
  const [stepReady, setStepReady] = useState(false);

  function clearTimers() {
    if (stepDelayRef.current !== null) window.clearTimeout(stepDelayRef.current);
    if (captureTimeoutRef.current !== null) window.clearTimeout(captureTimeoutRef.current);
    stepDelayRef.current = null;
    captureTimeoutRef.current = null;
  }

  function armStepAction() {
    if (stepDelayRef.current !== null) window.clearTimeout(stepDelayRef.current);
    setStepReady(false);
    stepDelayRef.current = window.setTimeout(() => setStepReady(true), minimumStepHoldMs);
  }

  useEffect(() => () => {
    clearTimers();
    discardRecordingRef.current = true;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    stopStream(streamRef.current);
  }, []);

  async function startCamera() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onError("Trình duyệt này chưa hỗ trợ ghi hình trực tiếp từ camera.");
      return;
    }
    setState("requesting");
    onRecorded(null);
    onError("");
    try {
      stopStream(streamRef.current);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 24, max: 30 },
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setState("ready");
    } catch (reason) {
      setState("idle");
      onError(cameraErrorMessage(reason));
    }
  }

  function stopRecording(discard = false) {
    clearTimers();
    discardRecordingRef.current = discard;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }

  function expireRecording() {
    stopRecording(true);
    onError("Phiên camera kéo dài quá lâu. Vui lòng thực hiện lại challenge khi bạn sẵn sàng.");
  }

  function startRecording() {
    const stream = streamRef.current;
    const mimeType = supportedRecorderMimeType();
    if (!stream || !mimeType) {
      onError("Trình duyệt không hỗ trợ định dạng ghi hình cần thiết.");
      return;
    }
    chunksRef.current = [];
    discardRecordingRef.current = false;
    onRecorded(null);
    onError("");
    const recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 1_500_000 });
    recorderRef.current = recorder;
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    });
    recorder.addEventListener("stop", () => {
      if (discardRecordingRef.current) {
        chunksRef.current = [];
        onRecorded(null);
        setState("ready");
        return;
      }
      const recordedType = recorder.mimeType || mimeType;
      const type = recordedType.startsWith("video/mp4") ? "video/mp4" : "video/webm";
      const extension = type === "video/mp4" ? "mp4" : "webm";
      const blob = new Blob(chunksRef.current, { type });
      if (!blob.size) {
        setState("ready");
        onError("Không ghi nhận được hình ảnh. Vui lòng thực hiện lại challenge.");
        return;
      }
      onRecorded(new File([blob], `live-challenge-${Date.now()}.${extension}`, { type }));
      setState("recorded");
    }, { once: true });
    recorder.start(250);
    setStepIndex(0);
    setState("recording");
    armStepAction();
    captureTimeoutRef.current = window.setTimeout(expireRecording, hiddenCaptureTimeoutMs);
  }

  function advanceChallenge() {
    if (!stepReady) return;
    if (stepIndex === guidedChallengeSteps.length - 1) {
      stopRecording(false);
      return;
    }
    setStepIndex((value) => value + 1);
    armStepAction();
  }

  const currentStep = guidedChallengeSteps[stepIndex];

  return (
    <div className="cameraPanel challengeCamera">
      <div className="cameraViewport selfieViewport">
        <video ref={videoRef} autoPlay muted playsInline aria-label="Camera challenge khuôn mặt" />
        {(state === "ready" || state === "recording" || state === "recorded") && <div className="faceGuide" aria-hidden="true" />}
        {state === "idle" && (
          <div className="cameraPlaceholder"><Video size={34} /><strong>Sẵn sàng thực hiện challenge?</strong><span>Bạn chủ động chuyển bước, không có bộ đếm thời gian trên màn hình.</span></div>
        )}
        {state === "requesting" && <div className="cameraPlaceholder"><LoaderCircle className="spin" /><span>Đang mở camera và microphone…</span></div>}
        {state === "recording" && (
          <div className="challengeOverlay">
            <span className="recordingBadge"><i /> ĐANG GHI</span>
            <strong>{currentStep.label}</strong>
            <small>{currentStep.detail}</small>
            {currentStep.showChallenge && <b>{challenge}</b>}
          </div>
        )}
        {state === "recorded" && <div className="recordedBadge"><Check size={19} /> Đã ghi đủ các bước</div>}
      </div>
      <div className="cameraToolbar">
        {state === "idle" || state === "requesting" ? (
          <button type="button" className="primaryButton" disabled={state === "requesting"} onClick={startCamera}><Video size={18} /> Bật camera và microphone</button>
        ) : state === "ready" ? (
          <button type="button" className="primaryButton" onClick={startRecording}><Video size={18} /> Bắt đầu challenge</button>
        ) : state === "recording" ? (
          <>
            <button type="button" className="secondaryButton compactButton" onClick={() => stopRecording(true)}><Square size={16} /> Hủy lượt này</button>
            <button type="button" className="primaryButton compactButton" disabled={!stepReady} onClick={advanceChallenge}><Check size={17} /> {currentStep.action}</button>
          </>
        ) : (
          <button type="button" className="secondaryButton" onClick={startRecording}><RefreshCw size={16} /> Thực hiện lại</button>
        )}
      </div>
    </div>
  );
}
