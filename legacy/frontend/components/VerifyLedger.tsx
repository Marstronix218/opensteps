"use client";

import { useState } from "react";
import { browserApiUrl } from "@/lib/api";
import { Status } from "./Status";

export function VerifyLedger({ tenantId, runId }: { tenantId: string; runId: string }) {
  const [result, setResult] = useState<{ verified: boolean; checked_events: number; errors: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  async function verify() {
    setLoading(true);
    const response = await fetch(`${browserApiUrl}/tenants/${tenantId}/ledger/verify`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ run_id: runId }),
    });
    setResult(await response.json());
    setLoading(false);
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      <button className="button" disabled={loading} onClick={verify}>{loading ? "Verifying..." : "Verify ledger"}</button>
      {result && <><Status value={result.verified ? "verified" : "failed"} /><span className="text-sm">{result.checked_events} events checked</span></>}
      {result?.errors.map((error) => <p className="w-full font-mono text-xs text-rust" key={error}>{error}</p>)}
    </div>
  );
}

