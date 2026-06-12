const serverUrl = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${serverUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "content-type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new Error(`OpenSteps API ${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export const browserApiUrl =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

