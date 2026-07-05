import { useState, useEffect } from "react";

type VerificationStatus =
  | "loading"
  | "valid"
  | "expired"
  | "used"
  | "invalid"
  | "already_confirmed"
  | "error";

function App() {
  const [token, setToken] = useState<string>("");
  const [route, setRoute] = useState<"confirm" | "resend-request" | "unknown">("confirm");
  const [status, setStatus] = useState<VerificationStatus>("loading");
  const [teamName, setTeamName] = useState<string>("");
  const [captainIgn, setCaptainIgn] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [processing, setProcessing] = useState<boolean>(false);

  // Parse path client-side
  useEffect(() => {
    const path = window.location.pathname;
    const confirmMatch = path.match(/^\/confirm\/([a-zA-Z0-9_-]+)/);
    const resendMatch = path.match(/^\/resend-request\/([a-zA-Z0-9_-]+)/);

    let currentToken = "";
    if (confirmMatch) {
      currentToken = confirmMatch[1];
      setRoute("confirm");
    } else if (resendMatch) {
      currentToken = resendMatch[1];
      setRoute("resend-request");
    } else {
      setRoute("unknown");
      setStatus("invalid");
      return;
    }

    setToken(currentToken);
    fetchStatus(currentToken);
  }, []);

  const fetchStatus = async (tok: string) => {
    try {
      const res = await fetch(`/api/status/${tok}`);
      if (!res.ok) throw new Error("Failed to fetch status");
      const data = await res.json();
      
      setStatus(data.status);
      if (data.team_name) setTeamName(data.team_name);
      if (data.captain_ign) setCaptainIgn(data.captain_ign);
    } catch (err) {
      logError(err);
      setStatus("error");
      setMessage("Failed to connect to the server. Please check your connection.");
    }
  };

  const logError = (err: unknown) => {
    console.error(err);
  };

  const handleConfirm = async () => {
    if (processing) return;
    setProcessing(true);
    try {
      const res = await fetch(`/api/confirm/${token}`, { method: "POST" });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Confirmation failed");
      }
      setStatus("already_confirmed"); // success state
      setMessage("Email confirmed successfully! Your registration is now active.");
    } catch (err: any) {
      logError(err);
      setMessage(err.message || "An error occurred during confirmation.");
    } finally {
      setProcessing(false);
    }
  };

  const handleResend = async () => {
    if (processing) return;
    setProcessing(true);
    try {
      const res = await fetch(`/api/resend/${token}`, { method: "POST" });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Resend request failed");
      }
      setStatus("used"); // treat as used/invalidated now that a new one is sent
      setMessage("A new confirmation email has been sent! Please check your inbox (and spam folder).");
    } catch (err: any) {
      logError(err);
      setMessage(err.message || "An error occurred while resending email.");
    } finally {
      setProcessing(false);
    }
  };

  // Render Loading
  if (status === "loading") {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-on-surface-variant font-medium">Verifying authorization token...</p>
        </div>
      </div>
    );
  }

  // Render Invalid / Unknown Route
  if (status === "invalid" || route === "unknown") {
    return (
      <div className="min-h-screen bg-background py-10 flex justify-center items-center px-4">
        <div className="w-full max-w-[600px] bg-white border border-outline-variant p-10 text-center shadow-sm">
          <h1 className="font-display-hero text-headline-lg text-primary uppercase mb-6">Invalid Token</h1>
          <p className="font-body-lg text-on-surface-variant mb-6">
            This verification link is invalid, corrupted, or does not exist.
          </p>
          <p className="font-label-sm text-on-surface-variant">
            Please make sure you copied the link exactly as it appears in the email.
          </p>
        </div>
      </div>
    );
  }

  // Main UI Shell
  return (
    <div className="w-full bg-background py-10 flex justify-center px-4">
      <div className="w-full max-w-[600px] bg-white border border-outline-variant shadow-sm">
        
        {/* Top Header Logo */}
        <div className="bg-primary h-20 flex items-center justify-center">
          <h1 className="font-display-hero text-[18px] tracking-[0.2em] text-on-primary uppercase font-bold">
            VALORANT TOURNAMENT SERIES
          </h1>
        </div>

        {/* Content Area */}
        <div className="p-10">
          
          {/* STATE: Valid Token (Normal Confirmation Flow) */}
          {status === "valid" && route === "confirm" && (
            <>
              <h2 className="font-headline-lg text-on-surface mb-stack-gap-sm">
                Welcome to the Tournament,{" "}
                <span className="text-primary font-bold">{captainIgn || "Captain"}</span>!
              </h2>
              <p className="font-body-lg text-on-surface-variant leading-relaxed mb-8">
                Your team <strong className="text-secondary">{teamName}</strong> has been successfully synchronized with our database. Just one last step: confirm your registration using the button below.
              </p>

              <div className="text-center mb-8">
                <button
                  onClick={handleConfirm}
                  disabled={processing}
                  className="w-full sm:w-auto inline-block bg-primary hover:bg-primary-container text-white font-display-hero text-label-caps px-10 py-4 uppercase tracking-widest transition-transform active:scale-95 disabled:opacity-50"
                >
                  {processing ? "Confirming..." : "confirm"}
                </button>
              </div>

              {message && (
                <div className="mb-8 p-4 bg-error-container text-on-error-container border border-error">
                  {message}
                </div>
              )}

              <div className="bg-surface-container-low border border-outline-variant p-6 flex flex-col gap-4 mb-8">
                <p className="font-label-sm text-on-surface-variant">
                  <strong>Note:</strong> Your registration token is secure. If you need to request a new verification link, use the button below.
                </p>
                <button
                  onClick={handleResend}
                  disabled={processing}
                  className="w-full border-2 border-secondary text-secondary hover:bg-secondary hover:text-white font-label-caps py-2 px-4 text-center transition-colors uppercase disabled:opacity-50"
                >
                  REQUEST NEW ACTIVATION TOKEN
                </button>
              </div>
            </>
          )}

          {/* STATE: Resend Request Specific Route */}
          {status === "valid" && route === "resend-request" && (
            <>
              <h2 className="font-headline-lg text-on-surface mb-stack-gap-sm">
                Request Activation Link
              </h2>
              <p className="font-body-lg text-on-surface-variant leading-relaxed mb-8">
                Request a new 1-hour verification email for team <strong className="text-secondary">{teamName}</strong>. This will automatically invalidate any previous links.
              </p>

              <div className="text-center mb-8">
                <button
                  onClick={handleResend}
                  disabled={processing}
                  className="w-full sm:w-auto inline-block bg-primary hover:bg-primary-container text-white font-display-hero text-label-caps px-10 py-4 uppercase tracking-widest transition-transform active:scale-95 disabled:opacity-50"
                >
                  {processing ? "Processing..." : "SEND NEW ACTIVATION LINK"}
                </button>
              </div>

              {message && (
                <div className="p-4 bg-surface-container-high text-on-surface border border-outline">
                  {message}
                </div>
              )}
            </>
          )}

          {/* STATE: Success / Already Confirmed */}
          {status === "already_confirmed" && (
            <div className="text-center py-6">
              <div className="text-5xl text-tertiary mb-4">✓</div>
              <h2 className="font-headline-lg text-on-surface mb-stack-gap-sm">
                Roster Confirmed!
              </h2>
              <p className="font-body-lg text-on-surface-variant leading-relaxed mb-8">
                The registration for <strong className="text-secondary">{teamName}</strong> is verified. You are authorized to begin the roster finalization phase.
              </p>
              {message && (
                <div className="p-4 bg-surface-container-low text-tertiary-container border border-tertiary-container text-left mb-6">
                  {message}
                </div>
              )}
              <p className="text-on-surface-variant font-label-sm">
                You can close this tab and return to the Discord thread to finish uploading your team logo.
              </p>
            </div>
          )}

          {/* STATE: Expired Link */}
          {status === "expired" && (
            <>
              <h2 className="font-headline-lg text-error mb-stack-gap-sm">
                Link Expired
              </h2>
              <p className="font-body-lg text-on-surface-variant leading-relaxed mb-8">
                The verification token for team <strong className="text-secondary">{teamName}</strong> has expired (valid for 1 hour).
              </p>

              <div className="text-center mb-8">
                <button
                  onClick={handleResend}
                  disabled={processing}
                  className="w-full sm:w-auto inline-block bg-primary hover:bg-primary-container text-white font-display-hero text-label-caps px-10 py-4 uppercase tracking-widest transition-transform active:scale-95 disabled:opacity-50"
                >
                  {processing ? "Sending..." : "REQUEST NEW LINK"}
                </button>
              </div>

              {message && (
                <div className="p-4 bg-surface-container-low text-on-surface-variant border border-outline mb-6">
                  {message}
                </div>
              )}
            </>
          )}

          {/* STATE: Used Link */}
          {status === "used" && (
            <div className="text-center py-6">
              <h2 className="font-headline-lg text-on-surface mb-stack-gap-sm">
                Link Invalidated
              </h2>
              <p className="font-body-lg text-on-surface-variant leading-relaxed mb-8">
                This verification link is no longer active. 
              </p>
              {message ? (
                <div className="p-4 bg-surface-container-low text-on-surface border border-outline mb-6">
                  {message}
                </div>
              ) : (
                <p className="text-on-surface-variant font-label-sm">
                  If you requested a new token, please check your inbox (and spam folders) for the newest email.
                </p>
              )}
            </div>
          )}

          {/* STATE: Server Connection Error */}
          {status === "error" && (
            <div className="text-center py-6">
              <h2 className="font-headline-lg text-error mb-stack-gap-sm">
                Connection Error
              </h2>
              <p className="font-body-lg text-on-surface-variant leading-relaxed mb-6">
                We could not connect to the verification server.
              </p>
              <div className="p-4 bg-error-container text-on-error-container border border-error mb-6">
                {message}
              </div>
              <button
                onClick={() => fetchStatus(token)}
                className="border-2 border-secondary text-secondary hover:bg-secondary hover:text-white font-label-caps py-2 px-4 transition-colors"
              >
                RETRY CONNECTION
              </button>
            </div>
          )}

          {/* Process List (Shown for active confirmation flows) */}
          {(status === "valid" || status === "expired") && (
            <div className="divider">
              <h3 className="section-title">Next Steps</h3>
              <div className="space-y-6">
                
                {/* Step 1 */}
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-white font-bold font-display-hero">1</div>
                  <div className="flex-grow">
                    <h4 className="font-body-md font-bold text-secondary">Complete Player Registration</h4>
                    <p className="font-label-sm text-on-surface-variant mb-2">Assign your 5 core players and 1 substitute via Discord ID.</p>
                    <div className="bg-[#2b2d31] p-3 rounded-md flex flex-wrap gap-2">
                      <span className="bg-primary/20 border border-primary text-primary text-[10px] px-2 py-1 rounded">PENDING...</span>
                    </div>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-white font-bold font-display-hero">2</div>
                  <div>
                    <h4 className="font-body-md font-bold text-secondary">Track Invitations</h4>
                    <p className="font-label-sm text-on-surface-variant">Monitor your roster dashboard to ensure all players have accepted the invite via the verification link.</p>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-white font-bold font-display-hero">3</div>
                  <div>
                    <h4 className="font-body-md font-bold text-secondary">Lock Your Roster</h4>
                    <p className="font-label-sm text-on-surface-variant">Once all 6 slots are verified, your roster will lock automatically for seeding.</p>
                  </div>
                </div>

              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="bg-secondary p-8 text-center text-secondary-fixed-dim">
          <div className="font-display-hero text-headline-md text-white tracking-tighter uppercase mb-4">
            VALORANT TOURNAMENT SERIES
          </div>
          <div className="flex justify-center gap-4 font-label-sm uppercase tracking-wider mb-6 text-slate-400 text-sm">
            <a className="hover:text-primary transition-colors" href="#">Support</a>
            <span className="opacity-30">|</span>
            <a className="hover:text-primary transition-colors" href="#">Tournament Rules</a>
            <span className="opacity-30">|</span>
            <a className="hover:text-primary transition-colors" href="#">Contact</a>
          </div>
          <p className="font-label-sm text-slate-500 text-xs leading-relaxed max-w-[400px] mx-auto">
            © 2026 VALORANT TOURNAMENT SERIES. ALL RIGHTS RESERVED. RIOT GAMES, VALORANT, AND ALL ASSOCIATED LOGOS ARE TRADEMARKS OR REGISTERED TRADEMARKS OF RIOT GAMES, INC.
          </p>
        </div>

      </div>
    </div>
  );
}

export default App;
