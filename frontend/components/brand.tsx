import Link from "next/link";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link className="brand" href="/" aria-label="V-ID eKYC">
      <span className="brandMark" aria-hidden="true"><i>V</i></span>
      {!compact && (
        <span className="brandText">
          <strong>V-ID</strong>
          <small>Identity verification</small>
        </span>
      )}
    </Link>
  );
}
