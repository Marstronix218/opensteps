export default function Home() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-20">
      <p className="label mb-4">Secure agent operations</p>
      <h1 className="max-w-3xl text-5xl font-black leading-[0.95] tracking-tight md:text-7xl">
        Every action authorized. Every record tamper-evident.
      </h1>
      <div className="panel mt-12 grid gap-6 p-8 md:grid-cols-2">
        <div>
          <p className="label">Get started</p>
          <p className="mt-3 leading-7">
            Run <code className="bg-ink px-2 py-1 text-signal">make demo</code>. The command
            prints tenant-specific dashboard links after exercising allow, approval, deny,
            checkpoint, and verification paths.
          </p>
        </div>
        <div className="border-l-0 border-line md:border-l md:pl-6">
          <p className="label">API documentation</p>
          <a className="mt-3 block text-xl font-bold underline" href="http://localhost:8000/docs">
            localhost:8000/docs
          </a>
          <p className="mt-3 text-sm text-ink/60">
            The dashboard intentionally requires a tenant ID. No cross-tenant discovery endpoint
            is exposed.
          </p>
        </div>
      </div>
    </main>
  );
}

