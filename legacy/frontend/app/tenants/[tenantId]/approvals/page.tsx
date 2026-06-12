import { ApprovalActions } from "@/components/ApprovalActions";
import { Status } from "@/components/Status";
import { TenantNav } from "@/components/TenantNav";
import { api } from "@/lib/api";
import type { Approval } from "@/lib/types";

export default async function ApprovalsPage({ params }: { params: Promise<{ tenantId: string }> }) {
  const { tenantId } = await params;
  const approvals = await api<Approval[]>(`/tenants/${tenantId}/approvals`);
  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <TenantNav tenantId={tenantId} />
      <p className="label">Human authorization gate</p><h1 className="mb-8 mt-2 text-4xl font-black">Approvals</h1>
      <div className="grid gap-5 lg:grid-cols-2">
        {approvals.map((approval) => (
          <article className="panel p-6" key={approval.id}>
            <div className="flex items-start justify-between gap-3"><code className="text-xs">{approval.id}</code><Status value={approval.status} /></div>
            <dl className="mt-5 grid gap-3 text-sm">
              {Object.entries(approval.scope_json).map(([key, value]) => <div key={key}><dt className="label">{key.replace("_", " ")}</dt><dd className="mt-1 break-all font-mono text-xs">{value}</dd></div>)}
            </dl>
            <p className="mt-4 text-xs text-ink/60">Expires {new Date(approval.expires_at).toLocaleString()}</p>
            {approval.status === "pending" && <ApprovalActions tenantId={tenantId} approvalId={approval.id} />}
          </article>
        ))}
      </div>
    </main>
  );
}

