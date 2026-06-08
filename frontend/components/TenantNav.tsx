import Link from "next/link";

export function TenantNav({ tenantId }: { tenantId: string }) {
  const links = ["runs", "approvals", "policies", "checkpoints"];
  return (
    <nav className="mb-8 flex flex-wrap gap-2 border-b border-line pb-4">
      {links.map((link) => (
        <Link
          key={link}
          href={`/tenants/${tenantId}/${link}`}
          className="border border-ink px-3 py-2 text-xs font-bold uppercase tracking-widest hover:bg-signal"
        >
          {link}
        </Link>
      ))}
    </nav>
  );
}

