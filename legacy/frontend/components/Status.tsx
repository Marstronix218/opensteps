export function Status({ value }: { value: string }) {
  const tone =
    value === "approved" || value === "completed" || value === "allowed" || value === "verified"
      ? "bg-signal"
      : value === "pending" || value === "approval_required"
        ? "bg-amber-300"
        : value === "denied" || value === "rejected" || value === "failed"
          ? "bg-rust text-white"
          : "bg-ink/10";
  return (
    <span className={`inline-block px-2 py-1 text-[10px] font-black uppercase tracking-wider ${tone}`}>
      {value}
    </span>
  );
}

