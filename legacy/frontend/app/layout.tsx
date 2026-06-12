import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenSteps Audit Console",
  description: "Authorization and tamper-evident audit for AI-agent actions",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="border-b-2 border-ink bg-ink text-paper">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
              <span className="grid h-8 w-8 place-items-center bg-signal font-black text-ink">OS</span>
              <div>
                <p className="font-black uppercase tracking-[0.18em]">OpenSteps</p>
                <p className="text-xs text-paper/60">Authorization & audit console</p>
              </div>
            </div>
            <span className="border border-paper/30 px-3 py-1 text-xs uppercase tracking-widest">
              MVP / Sandbox
            </span>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}

