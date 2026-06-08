import { TenantNav } from "@/components/TenantNav";
import { api } from "@/lib/api";
import type { Checkpoint } from "@/lib/types";

export default async function CheckpointsPage({ params }: { params: Promise<{ tenantId: string }> }) {
  const { tenantId } = await params;
  const checkpoints = await api<Checkpoint[]>(`/tenants/${tenantId}/checkpoints`);
  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <TenantNav tenantId={tenantId} />
      <p className="label">Signed ledger boundaries</p><h1 className="mb-8 mt-2 text-4xl font-black">Checkpoints</h1>
      <div className="space-y-5">
        {checkpoints.map((checkpoint) => (
          <article className="panel grid gap-5 p-6 md:grid-cols-[180px_1fr]" key={checkpoint.id}>
            <div><p className="text-5xl font-black">{checkpoint.event_count}</p><p className="label mt-1">events sealed</p><p className="mt-4 text-xs">{new Date(checkpoint.created_at).toLocaleString()}</p></div>
            <div className="space-y-3">
              <div><p className="label">Merkle root</p><p className="hash">{checkpoint.merkle_root}</p></div>
              <div><p className="label">Event range</p><p className="hash">{checkpoint.from_event_id} → {checkpoint.to_event_id}</p></div>
              <div><p className="label">Ed25519 service signature</p><p className="hash">{checkpoint.signature}</p></div>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}

