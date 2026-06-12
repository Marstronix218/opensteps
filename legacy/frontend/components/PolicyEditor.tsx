"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { browserApiUrl } from "@/lib/api";
import type { Policy } from "@/lib/types";

const starter = `default: deny\n\nrules:\n  - effect: allow\n    agent: code-agent\n    tool: github\n    actions: [create_pull_request]\n    resources: [repo:example/app]\n`;

export function PolicyEditor({ tenantId, policy }: { tenantId: string; policy?: Policy }) {
  const router = useRouter();
  const [name, setName] = useState(policy?.name || "Agent policy");
  const [yaml, setYaml] = useState(policy?.policy_yaml || starter);
  const [message, setMessage] = useState("");
  async function save() {
    const path = policy ? `/tenants/${tenantId}/policies/${policy.id}` : `/tenants/${tenantId}/policies`;
    const response = await fetch(`${browserApiUrl}${path}`, {
      method: policy ? "PUT" : "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name, policy_yaml: yaml }),
    });
    setMessage(response.ok ? "Policy saved" : await response.text());
    if (response.ok) router.refresh();
  }
  return (
    <div className="panel p-5">
      <input className="mb-3 w-full border border-ink bg-transparent p-2 font-bold" value={name} onChange={(e) => setName(e.target.value)} />
      <textarea className="h-80 w-full border border-ink bg-[#fffdf5] p-4 font-mono text-xs leading-5" value={yaml} onChange={(e) => setYaml(e.target.value)} spellCheck={false} />
      <div className="mt-3 flex items-center gap-3"><button className="button" onClick={save}>Save policy</button><span className="text-xs">{message}</span></div>
    </div>
  );
}

