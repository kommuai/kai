import { Outlet, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { tenantsApi } from "../lib/api";
import Spinner from "./Spinner";

export default function TenantShell() {
  const { slug } = useParams<{ slug: string }>();

  const { data: tenant, isLoading } = useQuery({
    queryKey: ["tenantBySlug", slug],
    queryFn: () => tenantsApi.getBySlug(slug!),
    enabled: !!slug,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="text-center py-20 text-gray-500 text-sm">Agent not found.</div>
    );
  }

  return <Outlet context={{ tenant }} />;
}
