"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { browserApiUrl } from "@/lib/api";

export function ApprovalActions({ tenantId, approvalId }: { tenantId: string; approvalId: string }) {
  const router = useRouter();
  const [userId, setUserId] = useState("");
  const [error, setError] = useState("");
  async function decide(action: "approve" | "reject") {
    setError("");
    const response = await fetch(`${browserApiUrl}/tenants/${tenantId}/approvals/${approvalId}/${action}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    router.refresh();
  }
  return (
    <div className="mt-4">
      <input className="w-full border border-ink bg-transparent p-2 text-xs" placeholder="Approver user UUID" value={userId} onChange={(e) => setUserId(e.target.value)} />
      <div className="mt-2 flex gap-2">
        <button className="button" disabled={!userId} onClick={() => decide("approve")}>Approve</button>
        <button className="border border-rust px-4 py-2 text-sm font-bold text-rust" disabled={!userId} onClick={() => decide("reject")}>Reject</button>
      </div>
      {error && <p className="mt-2 text-xs text-rust">{error}</p>}
    </div>
  );
}

