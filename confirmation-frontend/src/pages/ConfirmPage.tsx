import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

// The Pi's FastAPI URL — set VITE_API_URL in Vercel env vars
const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

type TokenStatus =
  | "loading"
  | "valid"
  | "expired"
  | "used"
  | "invalid"
  | "already_confirmed"
  | "confirmed"
  | "confirming"
  | "resending"
  | "resent"
  | "error";

interface StatusData {
  status: TokenStatus;
  team_name?: string;
  captain_ign?: string;
  expires_at?: string;
  errorMsg?: string;
}

// ── Reusable layout shell ─────────────────────────────────────────────────────

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: "100vh", background: "#f3f4f6", display: "flex", justifyContent: "center", padding: "40px 16px" }}>
      <div style={{ width: "100%", maxWidth: 600, background: "#ffffff" }}>
        {/* Header */}
        <div style={{
          background: "var(--primary)", padding: "28px 40px", textAlign: "center",
        }}>
          <h1 style={{
            margin: 0, fontFamily: "var(--font-display)", fontSize: 16,
            fontWeight: 800, letterSpacing: "0.22em", color: "#fff",
            textTransform: "uppercase",
          }}>
            VALORANT TOURNAMENT SERIES
          </h1>
        </div>

        {/* Body */}
        <div style={{ padding: "32px 40px" }}>{children}</div>

        {/* Footer */}
        <div style={{ background: "var(--secondary)", padding: "28px 40px", textAlign: "center" }}>
          <div style={{
            fontFamily: "var(--font-display)", fontSize: 16, fontWeight: 700,
            color: "#fff", textTransform: "uppercase", letterSpacing: "-0.01em",
            marginBottom: 12,
          }}>
            VALORANT TOURNAMENT SERIES
          </div>
          <div style={{
            fontFamily: "var(--font-body)", fontSize: 11, color: "var(--muted)",
            lineHeight: 1.6, maxWidth: 400, margin: "0 auto",
          }}>
            © 2026 VALORANT TOURNAMENT SERIES. ALL RIGHTS RESERVED. RIOT GAMES, VALORANT,
            AND ALL ASSOCIATED LOGOS ARE TRADEMARKS OR REGISTERED TRADEMARKS OF RIOT GAMES, INC.
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Button ────────────────────────────────────────────────────────────────────

function Btn({
  onClick, disabled = false, variant = "primary", children,
}: {
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "outline";
  children: React.ReactNode;
}) {
  const base: React.CSSProperties = {
    display: "inline-block", cursor: disabled ? "not-allowed" : "pointer",
    fontFamily: "var(--font-display)", fontSize: 12, fontWeight: 800,
    letterSpacing: "0.12em", textTransform: "uppercase", border: "none",
    padding: "16px 44px", opacity: disabled ? 0.6 : 1,
    transition: "opacity 0.15s",
  };
  const styles: Record<string, React.CSSProperties> = {
    primary: { ...base, background: "var(--primary)", color: "#fff" },
    outline: { ...base, background: "transparent", border: "2px solid var(--secondary)", color: "var(--secondary)", padding: "8px 20px" },
  };
  return (
    <button style={styles[variant]} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

// ── Step list ─────────────────────────────────────────────────────────────────

function Steps() {
  const steps = [
    { n: 1, title: "Complete Player Registration", desc: "Assign your 5 core players and 1 substitute via Discord." },
    { n: 2, title: "Track Invitations", desc: "Monitor your roster to ensure all players have accepted the invite." },
    { n: 3, title: "Lock Your Roster", desc: "Once all 6 slots are verified, your roster will lock automatically." },
  ];
  return (
    <div style={{ borderTop: "1px solid var(--outline)", paddingTop: 24, marginTop: 8 }}>
      <h3 style={{
        margin: "0 0 20px", fontFamily: "var(--font-display)", fontSize: 18,
        fontWeight: 700, color: "var(--secondary)", textTransform: "uppercase",
      }}>
        Next Steps
      </h3>
      {steps.map((s) => (
        <div key={s.n} style={{ display: "flex", gap: 16, marginBottom: 20 }}>
          <div style={{
            flexShrink: 0, width: 40, height: 40, borderRadius: "50%",
            background: "var(--secondary)", color: "#fff",
            fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>{s.n}</div>
          <div>
            <div style={{ fontFamily: "var(--font-body)", fontWeight: 700, fontSize: 15, color: "var(--secondary)", marginBottom: 3 }}>
              {s.title}
            </div>
            <div style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--on-surface-variant)", lineHeight: 1.5 }}>
              {s.desc}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ConfirmPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<StatusData>({ status: "loading" });

  // Check token status on mount
  useEffect(() => {
    if (!token) { setData({ status: "invalid" }); return; }
    fetch(`${API_URL}/api/status/${token}`)
      .then((r) => r.json())
      .then((json) => setData({ ...json }))
      .catch(() => setData({ status: "error", errorMsg: "Could not reach the confirmation server." }));
  }, [token]);

  // ── Confirm action ──────────────────────────────────────────────────────────
  const handleConfirm = async () => {
    setData((d) => ({ ...d, status: "confirming" }));
    try {
      const r = await fetch(`${API_URL}/api/confirm/${token}`, { method: "POST" });
      const json = await r.json();
      if (!r.ok) setData({ status: "error", errorMsg: json.detail ?? "Confirmation failed." });
      else setData({ status: "confirmed", team_name: json.team_name });
    } catch {
      setData({ status: "error", errorMsg: "Network error. Please try again." });
    }
  };

  // ── Resend action ───────────────────────────────────────────────────────────
  const handleResend = async () => {
    setData((d) => ({ ...d, status: "resending" }));
    try {
      const r = await fetch(`${API_URL}/api/resend/${token}`, { method: "POST" });
      const json = await r.json();
      if (!r.ok) setData({ status: "error", errorMsg: json.detail ?? "Resend failed." });
      else setData({ status: "resent" });
    } catch {
      setData({ status: "error", errorMsg: "Network error. Please try again." });
    }
  };

  // ── Render states ───────────────────────────────────────────────────────────

  if (data.status === "loading") {
    return (
      <Shell>
        <p style={{ textAlign: "center", color: "var(--on-surface-variant)", padding: "40px 0" }}>
          Checking your confirmation link…
        </p>
      </Shell>
    );
  }

  if (data.status === "confirmed") {
    return (
      <Shell>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: "#00C851", margin: "0 0 12px" }}>
          Registration Confirmed!
        </h2>
        <p style={{ fontSize: 17, lineHeight: 1.6, color: "var(--on-surface-variant)", marginBottom: 28 }}>
          <strong style={{ color: "var(--on-surface)" }}>{data.team_name}</strong> has been confirmed.
          Staff will review your application and reach out shortly.
        </p>
        <Steps />
      </Shell>
    );
  }

  if (data.status === "already_confirmed") {
    return (
      <Shell>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: "var(--on-surface)", margin: "0 0 12px" }}>
          Already Confirmed
        </h2>
        <p style={{ fontSize: 17, lineHeight: 1.6, color: "var(--on-surface-variant)", marginBottom: 28 }}>
          <strong style={{ color: "var(--on-surface)" }}>{data.team_name}</strong> has already been confirmed.
          No further action needed.
        </p>
        <Steps />
      </Shell>
    );
  }

  if (data.status === "resent") {
    return (
      <Shell>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: "var(--on-surface)", margin: "0 0 12px" }}>
          New Email Sent
        </h2>
        <p style={{ fontSize: 17, lineHeight: 1.6, color: "var(--on-surface-variant)" }}>
          A new confirmation email has been sent. Please check your inbox and spam folder.
          The new link is valid for <strong>1 hour</strong>.
        </p>
      </Shell>
    );
  }

  if (data.status === "expired") {
    return (
      <Shell>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: "var(--on-surface)", margin: "0 0 12px" }}>
          Link Expired
        </h2>
        <p style={{ fontSize: 17, lineHeight: 1.6, color: "var(--on-surface-variant)", marginBottom: 24 }}>
          This confirmation link has expired. Request a new one below — it will be valid for another hour.
        </p>
        <Btn onClick={handleResend} disabled={data.status === ("resending" as TokenStatus)} variant="outline">
          {data.status === ("resending" as TokenStatus) ? "Sending…" : "REQUEST NEW ACTIVATION TOKEN"}
        </Btn>
      </Shell>
    );
  }

  if (data.status === "used" || data.status === "invalid") {
    return (
      <Shell>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: "var(--on-surface)", margin: "0 0 12px" }}>
          {data.status === "used" ? "Link Already Used" : "Invalid Link"}
        </h2>
        <p style={{ fontSize: 17, lineHeight: 1.6, color: "var(--on-surface-variant)" }}>
          {data.status === "used"
            ? "This confirmation link has already been used. If you need help, contact a moderator."
            : "This confirmation link is invalid or does not exist."}
        </p>
      </Shell>
    );
  }

  if (data.status === "error") {
    return (
      <Shell>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: "var(--primary)", margin: "0 0 12px" }}>
          Something went wrong
        </h2>
        <p style={{ fontSize: 17, lineHeight: 1.6, color: "var(--on-surface-variant)" }}>
          {data.errorMsg ?? "An unexpected error occurred. Please try again or contact a moderator."}
        </p>
      </Shell>
    );
  }

  // ── Default: valid token ──────────────────────────────────────────────────
  return (
    <Shell>
      {/* Welcome */}
      <h2 style={{
        fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700,
        color: "var(--on-surface)", margin: "0 0 12px",
      }}>
        Welcome to the Tournament,{" "}
        <span style={{ color: "var(--primary)" }}>{data.captain_ign}</span>!
      </h2>
      <p style={{ fontSize: 17, lineHeight: 1.6, color: "var(--on-surface-variant)", marginBottom: 28 }}>
        Your team provisioning has been successfully synchronized with our tournament database.
        Click <strong>Confirm</strong> below to complete your registration.
      </p>

      {/* CTA */}
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <Btn
          onClick={handleConfirm}
          disabled={data.status === "confirming"}
        >
          {data.status === "confirming" ? "Confirming…" : "Confirm"}
        </Btn>
      </div>

      {/* Info box */}
      <div style={{
        background: "var(--surface-low)", border: "1px solid var(--outline)",
        padding: 16, marginBottom: 28,
      }}>
        <p style={{ margin: "0 0 12px", fontFamily: "var(--font-body)", fontSize: 14, lineHeight: 1.5, color: "var(--on-surface-variant)" }}>
          <strong>Note:</strong> This link is valid for 1 hour. If it expires, request a new one below.
        </p>
        <Btn onClick={handleResend} disabled={data.status === "resending"} variant="outline">
          {data.status === "resending" ? "Sending…" : "REQUEST NEW ACTIVATION TOKEN"}
        </Btn>
      </div>

      <Steps />
    </Shell>
  );
}
