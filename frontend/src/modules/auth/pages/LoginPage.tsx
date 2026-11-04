import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { authStore } from "@/app/store/authStore";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ErrorState } from "@/shared/components/ErrorState/ErrorState";
import { AlertTriangle, Eye, EyeOff, Loader2, Lock, LogIn, Mail, ShieldCheck } from "lucide-react";

// Only the email is kept here, never the password or a token. It lives under its
// own key so clearing the session (logout, expired token) does not wipe it.
const LAST_EMAIL_KEY = "mis_master_last_email";

function readLastEmail(): string {
  if (typeof window === "undefined") return "";
  try {
    return window.localStorage.getItem(LAST_EMAIL_KEY) ?? "";
  } catch {
    return "";
  }
}

function saveLastEmail(email: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (email) window.localStorage.setItem(LAST_EMAIL_KEY, email);
    else window.localStorage.removeItem(LAST_EMAIL_KEY);
  } catch {
    // Private mode or blocked storage: signing in still works without it.
  }
}

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState(readLastEmail);
  const [hadSavedEmail] = useState(() => readLastEmail() !== "");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(true);
  const [capsLock, setCapsLock] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const cleanEmail = email.trim();
    if (!cleanEmail || !password) {
      setError("Please enter email and password.");
      return;
    }

    setLoading(true);
    try {
      await authStore.login(cleanEmail, password, remember);
      // "Keep me signed in" off usually means a shared computer, so forget the email too.
      saveLastEmail(remember ? cleanEmail : null);
      navigate({ to: "/dashboard/agent" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="relative w-full max-w-md overflow-hidden p-6 sm:p-10 space-y-8 shadow-card-hover animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="absolute inset-x-0 top-0 h-1 bg-primary" />

      <div className="space-y-4">
        <div className="h-11 w-11 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <div className="space-y-1.5">
          <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="text-sm text-muted-foreground">Sign in with your MIS Master email and password.</p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <div className="group relative">
            <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
            <Input
              id="email"
              type="email"
              autoComplete="username"
              placeholder="you@company.com"
              autoFocus={!hadSavedEmail}
              className="h-11 pl-10"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <div className="group relative">
            <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
            <Input
              id="password"
              type={show ? "text" : "password"}
              autoComplete="current-password"
              placeholder="Enter your password"
              autoFocus={hadSavedEmail}
              className="h-11 pl-10 pr-10"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyUp={(e) => setCapsLock(e.getModifierState("CapsLock"))}
              onBlur={() => setCapsLock(false)}
            />
            <button
              type="button"
              onClick={() => setShow((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors p-1.5 rounded-md"
              aria-label={show ? "Hide password" : "Show password"}
            >
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {capsLock && (
            <p className="flex items-center gap-1.5 text-xs text-warning" role="status">
              <AlertTriangle className="h-3.5 w-3.5" /> Caps Lock is on
            </p>
          )}
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer w-fit">
          <Checkbox checked={remember} onCheckedChange={(v) => setRemember(!!v)} />
          Keep me signed in
        </label>

        {error && <ErrorState title="Couldn't sign you in" message={error} />}

        <Button type="submit" className="w-full h-11 text-sm" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Signing in...
            </>
          ) : (
            <>
              <LogIn className="h-4 w-4 mr-2" /> Sign in
            </>
          )}
        </Button>
      </form>

      <div className="space-y-3">
        <div className="flex items-center gap-3 text-[11px] uppercase tracking-wider text-muted-foreground/70">
          <span className="h-px flex-1 bg-border" />
          Need access?
          <span className="h-px flex-1 bg-border" />
        </div>
        <p className="text-center text-xs text-muted-foreground">
          No account yet? Ask your MIS admin to create one for you.
        </p>
      </div>
    </Card>
  );
}
