import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";
import { tenantsApi, type Tenant } from "../lib/api";
import { formatApiError } from "../lib/apiErrors";
import Spinner from "./Spinner";

interface DeleteTenantPanelProps {
  tenant: Tenant;
  /** After delete, navigate here (default /dashboard) */
  redirectTo?: string;
  className?: string;
}

export default function DeleteTenantPanel({ tenant, redirectTo = "/dashboard", className }: DeleteTenantPanelProps) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [confirmSlug, setConfirmSlug] = useState("");
  const [deleteWorkspace, setDeleteWorkspace] = useState(false);
  const [open, setOpen] = useState(false);

  const canDelete = confirmSlug === tenant.slug;

  const deleteMut = useMutation({
    mutationFn: () => tenantsApi.delete(tenant.id, { deleteWorkspace }),
    onSuccess: () => {
      toast.success(
        deleteWorkspace ? "Tenant and workspace folder removed" : "Tenant removed from Studio",
      );
      qc.invalidateQueries({ queryKey: ["tenants"] });
      qc.removeQueries({ queryKey: ["tenantBySlug", tenant.slug] });
      navigate(redirectTo, { replace: true });
    },
    onError: (err) => toast.error(formatApiError(err, "Could not delete tenant")),
  });

  if (!open) {
    return (
      <div className={clsx("card p-5 border border-red-100", className)}>
        <div className="flex items-start gap-3">
          <div className="h-9 w-9 rounded-xl bg-red-50 flex items-center justify-center shrink-0">
            <AlertTriangle size={18} className="text-red-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 text-sm">Delete tenant</h3>
            <p className="text-xs text-gray-500 mt-1">
              Remove <strong>{tenant.display_name}</strong> from Kai Studio. Workspace files on disk are kept
              unless you choose to delete them.
            </p>
          </div>
          <button type="button" className="btn-danger btn-sm shrink-0" onClick={() => setOpen(true)}>
            <Trash2 size={14} />
            Delete
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx("card p-5 border border-red-200 bg-red-50/30", className)}>
      <h3 className="font-semibold text-red-900 text-sm flex items-center gap-2">
        <AlertTriangle size={16} />
        Confirm deletion
      </h3>
      <p className="text-xs text-red-800/90 mt-2 leading-relaxed">
        This removes the tenant from Studio (memberships, invites, contact tags). Inbox data in{" "}
        <code className="font-mono text-[11px] bg-white/60 px-1 rounded">sessions.db</code> is not deleted by
        this action.
      </p>

      <label className="mt-4 flex items-start gap-2 cursor-pointer">
        <input
          type="checkbox"
          className="mt-0.5 rounded border-red-300"
          checked={deleteWorkspace}
          onChange={(e) => setDeleteWorkspace(e.target.checked)}
        />
        <span className="text-xs text-gray-700">
          Also delete workspace folder on disk:{" "}
          <code className="font-mono text-[10px] break-all">{tenant.workspace_home}</code>
        </span>
      </label>

      <div className="mt-4">
        <label className="label text-red-900">
          Type <span className="font-mono font-semibold">{tenant.slug}</span> to confirm
        </label>
        <input
          className="input border-red-200 focus:border-red-500 focus:ring-red-500/30"
          value={confirmSlug}
          onChange={(e) => setConfirmSlug(e.target.value)}
          placeholder={tenant.slug}
          autoComplete="off"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2 justify-end">
        <button
          type="button"
          className="btn-secondary btn-sm"
          disabled={deleteMut.isPending}
          onClick={() => {
            setOpen(false);
            setConfirmSlug("");
            setDeleteWorkspace(false);
          }}
        >
          Cancel
        </button>
        <button
          type="button"
          className="btn-danger btn-sm"
          disabled={!canDelete || deleteMut.isPending}
          onClick={() => deleteMut.mutate()}
        >
          {deleteMut.isPending ? <Spinner size="sm" className="text-white" /> : <Trash2 size={14} />}
          Delete permanently
        </button>
      </div>
    </div>
  );
}
