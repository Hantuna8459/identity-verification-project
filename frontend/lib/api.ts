export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v2";
export const VID_CLIENT_KEY = process.env.NEXT_PUBLIC_VID_CLIENT_KEY ?? "local-vid-client-key";
export const WEB_CAPTURE_ENABLED =
  process.env.NEXT_PUBLIC_WEB_CAPTURE_ENABLED === "true" ||
  (process.env.NEXT_PUBLIC_WEB_CAPTURE_ENABLED === undefined && process.env.NODE_ENV === "development");

export type SessionState = {
  id: string;
  document_type: string;
  stage: string;
  decision: string;
  voice_challenge: string | null;
  next_action: string;
  expires_at: string;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let message = `Yêu cầu thất bại (${response.status})`;
    try {
      const payload = await response.json();
      message = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    } catch {}
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}
