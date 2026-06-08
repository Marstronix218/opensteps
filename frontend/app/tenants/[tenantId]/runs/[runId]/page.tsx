import { Status } from "@/components/Status";
import { TenantNav } from "@/components/TenantNav";
import { VerifyLedger } from "@/components/VerifyLedger";
import { api } from "@/lib/api";
import type { Run } from "@/lib/types";

const short = (value: string | null) => value ? `${value.slice(0, 12)}…${value.slice(-8)}` : "—";

export default async function RunDetailPage({ params }: { params: Promise<{ tenantId: string; runId: string }> }) {
  const { tenantId, runId } = await params;
  const run = await api<Run>(`/tenants/${tenantId}/runs/${runId}`);
  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <TenantNav tenantId={tenantId} />
      <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
        <div><p className="label">Run evidence</p><h1 className="mt-2 text-3xl font-black">{run.id}</h1></div>
        <VerifyLedger tenantId={tenantId} runId={runId} />
      </div>
      <div className="space-y-4">
        {run.events?.map((event, index) => (
          <article className="panel grid gap-5 p-5 lg:grid-cols-[64px_240px_1fr]" key={event.id}>
            <div className="grid h-12 w-12 place-items-center border-2 border-ink bg-signal font-black">{String(index + 1).padStart(2, "0")}</div>
            <div>
              <p className="label">{new Date(event.timestamp).toLocaleString()}</p>
              <h2 className="mt-2 font-black">{event.event_type}</h2>
              {event.policy_decision && <div className="mt-3"><Status value={event.policy_decision} /></div>}
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <div><p className="label">Actor</p><p className="mt-1 font-mono text-xs">{event.agent_id || event.user_id || "service"}</p></div>
              <div><p className="label">Operation</p><p className="mt-1 text-sm">{event.tool ? `${event.tool}.${event.action}` : "—"}</p></div>
              <div><p className="label">Resource</p><p className="mt-1 text-sm">{event.resource || "—"}</p></div>
              <div><p className="label">Input / output hash</p><p className="hash">{short(event.input_hash)} / {short(event.output_hash)}</p></div>
              <div><p className="label">Event hash</p><p className="hash" title={event.event_hash}>{event.event_hash}</p></div>
              <div><p className="label">Previous hash</p><p className="hash" title={event.previous_hash || ""}>{event.previous_hash || "GENESIS"}</p></div>
              <div><p className="label">Approval</p><p className="hash">{event.approval_id || "—"}</p></div>
              <div><p className="label">Agent signature</p><p className="text-sm">{event.signature ? "Present (request-bound)" : "Not applicable"}</p></div>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}

