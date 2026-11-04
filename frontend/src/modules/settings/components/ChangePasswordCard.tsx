import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/shared/components/ErrorState/ErrorState";
import { changePassword } from "@/services/api/auth";
import { getErrorMessage } from "@/lib/api-client";
import { CheckCircle2, Eye, EyeOff, KeyRound, Loader2 } from "lucide-react";

const MIN_LENGTH = 8;
const MAX_LENGTH = 128;

interface PasswordFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  show: boolean;
  onToggle: () => void;
  hint?: string;
}

function PasswordField({ id, label, value, onChange, autoComplete, show, onToggle, hint }: PasswordFieldProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={show ? "text" : "password"}
          autoComplete={autoComplete}
          className="h-10 pr-10"
          maxLength={MAX_LENGTH}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1.5 rounded-md"
          aria-label={show ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function ChangePasswordCard() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: () => changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setShowCurrent(false);
      setShowNew(false);
      setShowConfirm(false);
      setSuccess(true);
    },
  });

  function validate(): string | null {
    if (!currentPassword || !newPassword || !confirmPassword) return "Please fill in all three fields.";
    if (newPassword.length < MIN_LENGTH) return `New password must be at least ${MIN_LENGTH} characters.`;
    if (newPassword === currentPassword) return "New password must be different from the current password.";
    if (newPassword !== confirmPassword) return "New password and confirmation do not match.";
    return null;
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSuccess(false);
    mutation.reset();
    const problem = validate();
    setFormError(problem);
    if (problem) return;
    mutation.mutate();
  }

  function clearMessages() {
    setSuccess(false);
    setFormError(null);
    if (mutation.isError) mutation.reset();
  }

  const serverError = mutation.isError ? getErrorMessage(mutation.error, "Unable to change the password.") : null;
  const error = formError ?? serverError;

  return (
    <Card className="p-6 shadow-card space-y-4">
      <div className="space-y-1">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Password</h3>
        <p className="text-sm text-muted-foreground">
          Change the password you use to sign in. You will stay signed in on this device.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-4 max-w-md" noValidate>
        <PasswordField
          id="current-password"
          label="Current password"
          autoComplete="current-password"
          value={currentPassword}
          onChange={(v) => {
            clearMessages();
            setCurrentPassword(v);
          }}
          show={showCurrent}
          onToggle={() => setShowCurrent((v) => !v)}
        />
        <PasswordField
          id="new-password"
          label="New password"
          autoComplete="new-password"
          value={newPassword}
          onChange={(v) => {
            clearMessages();
            setNewPassword(v);
          }}
          show={showNew}
          onToggle={() => setShowNew((v) => !v)}
          hint={`At least ${MIN_LENGTH} characters.`}
        />
        <PasswordField
          id="confirm-password"
          label="Confirm new password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(v) => {
            clearMessages();
            setConfirmPassword(v);
          }}
          show={showConfirm}
          onToggle={() => setShowConfirm((v) => !v)}
        />

        {error && <ErrorState title="Couldn't change password" message={error} />}

        {success && (
          <p className="flex items-center gap-2 text-sm text-success" role="status">
            <CheckCircle2 className="h-4 w-4 shrink-0" /> Your password has been changed.
          </p>
        )}

        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Updating...
            </>
          ) : (
            <>
              <KeyRound className="h-4 w-4 mr-2" /> Update password
            </>
          )}
        </Button>
      </form>
    </Card>
  );
}
