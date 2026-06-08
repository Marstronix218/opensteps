import Link from "next/link";
import { TenantNav } from "@/components/TenantNav";
import { Status } from "@/components/Status";
import { api } from "@/lib/api";
import type { Run } from "@/lib/types";

export default async function RunsPage({ params }: { params: Promise<{ tenantId: string }> }) {
  const { tenantId } = await params;
  const runs = await api<Run[]>(`/tenants/${tenantId}/runs`);
  const details = await Promise.all(
    runs.map(async (run) => {
      const detail = await api<Run>(`/tenants/${tenantId}/runs/${run.id}`);
      const verification = await api<{ verified: boolean }>(`/tenants/${tenantId}/ledger/verify`, {
        method: "POST",
        body: JSON.stringify({ run_id: run.id }),
      });
      return { ...detail, verified: verification.verified };
    }),
  );

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <TenantNav tenantId={tenantId} />
      <div className="mb-8">
        <p className="label">Tenant {tenantId}</p>
        <h1 className="mt-2 text-4xl font-black">Agent runs</h1>
      </div>
      <div className="panel overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b-2 border-ink bg-ink text-paper">
            <tr>{["Run ID", "Status", "Started", "Root agent", "Events", "Ledger"].map((h) => <th className="p-4 label text-paper/70" key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {details.map((run) => (
              <tr className="border-b border-line last:border-0" key={run.id}>
                <td className="p-4 font-mono text-xs"><Link className="underline" href={`/tenants/${tenantId}/runs/${run.id}`}>{run.id}</Link></td>
                <td className="p-4"><Status value={run.status} /></td>
                <td className="p-4">{new Date(run.started_at).toLocaleString()}</td>
                <td className="p-4 font-mono text-xs">{run.root_agent_id || "system"}</td>
                <td className="p-4 font-bold">{run.events?.length || 0}</td>
                <td className="p-4"><Status value={run.verified ? "verified" : "failed"} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!details.length && <p className="p-8 text-ink/60">No runs yet. Execute <code>make demo</code>.</p>}
      </div>
    </main>
  );
}

