import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Building2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { tenantsApi } from "../lib/api";
import Spinner from "../components/Spinner";

function slugify(s: string) {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 50);
}

export default function NewTenantPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [displayName, setDisplayName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);

  function handleNameChange(v: string) {
    setDisplayName(v);
    if (!slugTouched) setSlug(slugify(v));
  }

  const { mutate, isPending } = useMutation({
    mutationFn: () => tenantsApi.create({ display_name: displayName, slug, description }),
    onSuccess: (tenant) => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
      toast.success("Tenant created!");
      navigate(`/tenants/${tenant.id}`);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to create tenant");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutate();
  }

  return (
    <div className="max-w-xl mx-auto animate-fade-in">
      <button onClick={() => navigate(-1)} className="btn-ghost mb-6 -ml-2 text-gray-500">
        <ArrowLeft size={16} />
        Back
      </button>

      <div className="flex items-center gap-4 mb-8">
        <div className="h-12 w-12 rounded-2xl bg-brand-50 flex items-center justify-center">
          <Building2 size={24} className="text-brand-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">New tenant</h1>
          <p className="text-sm text-gray-500">
            A workspace will be scaffolded with a default configuration.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card p-6 space-y-5">
        <div>
          <label className="label" htmlFor="display_name">Display name</label>
          <input
            id="display_name"
            className="input"
            type="text"
            placeholder="Acme Support"
            value={displayName}
            onChange={(e) => handleNameChange(e.target.value)}
            required
            maxLength={60}
          />
        </div>

        <div>
          <label className="label" htmlFor="slug">Slug</label>
          <div className="relative">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm select-none pointer-events-none">
              kai-tenant-
            </span>
            <input
              id="slug"
              className="input pl-[7.5rem]"
              type="text"
              placeholder="acme"
              value={slug}
              onChange={(e) => { setSlugTouched(true); setSlug(slugify(e.target.value)); }}
              required
              pattern="[a-z0-9][a-z0-9-]{1,48}[a-z0-9]"
              title="Lowercase letters, numbers and hyphens (3–50 chars)"
            />
          </div>
          <p className="mt-1.5 text-xs text-gray-400">
            Workspace directory: <code className="font-mono bg-gray-100 px-1 py-0.5 rounded">~/workspace/kai-tenant-{slug || "…"}</code>
          </p>
        </div>

        <div>
          <label className="label" htmlFor="description">
            Description <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <textarea
            id="description"
            className="input resize-none"
            rows={2}
            placeholder="A short description of this tenant's bot"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={200}
          />
        </div>

        <button type="submit" disabled={isPending} className="btn-primary btn-lg w-full">
          {isPending ? <Spinner size="sm" className="text-white" /> : (
            <>
              Create tenant
              <ArrowRight size={18} />
            </>
          )}
        </button>
      </form>
    </div>
  );
}
