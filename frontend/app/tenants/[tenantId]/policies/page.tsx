import { PolicyEditor } from "@/components/PolicyEditor";
import { TenantNav } from "@/components/TenantNav";
import { api } from "@/lib/api";
import type { Policy } from "@/lib/types";

export default async function PoliciesPage({ params }: { params: Promise<{ tenantId: string }> }) {
  const { tenantId } = await params;
  const policies = await api<Policy[]>(`/tenants/${tenantId}/policies`);
  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <TenantNav tenantId={tenantId} />
      <p className="label">Enforcement rules</p><h1 className="mb-8 mt-2 text-4xl font-black">Policies</h1>
      <div className="grid gap-6 lg:grid-cols-2">
        {policies.map((policy) => <PolicyEditor tenantId={tenantId} policy={policy} key={policy.id} />)}
        <PolicyEditor tenantId={tenantId} />
      </div>
    </main>
  );
}

