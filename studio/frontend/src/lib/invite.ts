import type { NavigateFunction } from "react-router-dom";
import toast from "react-hot-toast";
import { tenantsApi, type Tenant } from "./api";
import { formatApiError } from "./apiErrors";

const PENDING_INVITE_KEY = "shadou_pending_invite_token";

export function setPendingInviteToken(token: string) {
  localStorage.setItem(PENDING_INVITE_KEY, token);
}

export function getPendingInviteToken(): string | null {
  return localStorage.getItem(PENDING_INVITE_KEY);
}

export function clearPendingInviteToken() {
  localStorage.removeItem(PENDING_INVITE_KEY);
}

/** After login/signup: accept stored invite or rely on server pending-by-email redeem. */
export async function finishAuthAndNavigate(
  navigate: NavigateFunction,
  opts?: { fallback?: string },
): Promise<void> {
  const token = getPendingInviteToken();
  if (token) {
    clearPendingInviteToken();
    try {
      const tenant = await tenantsApi.acceptInvite(token);
      toast.success(`Joined ${tenant.display_name}`);
      navigate(`/t/${tenant.slug}/inbox`, { replace: true });
      return;
    } catch (err: unknown) {
      toast.error(formatApiError(err, "Could not accept invite. Try opening your invite link again."));
    }
  }
  navigate(opts?.fallback ?? "/dashboard", { replace: true });
}

export async function acceptInviteToken(
  token: string,
  navigate: NavigateFunction,
): Promise<Tenant | null> {
  try {
    const tenant = await tenantsApi.acceptInvite(token);
    clearPendingInviteToken();
    toast.success(`Joined ${tenant.display_name}`);
    navigate(`/t/${tenant.slug}/inbox`, { replace: true });
    return tenant;
  } catch (err: unknown) {
    toast.error(formatApiError(err, "Could not accept invite."));
    return null;
  }
}
