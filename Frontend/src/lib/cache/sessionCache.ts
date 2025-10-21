// Frontend/src/lib/cache/sessionCache.ts
type Entry<T> = { value: T; exp: number };

export function scSet<T>(key: string, value: T, ttlMs: number): void {
  const payload: Entry<T> = { value, exp: Date.now() + ttlMs };
  sessionStorage.setItem(key, JSON.stringify(payload));
}

export function scGet<T>(key: string): T | undefined {
  const raw = sessionStorage.getItem(key);
  if (!raw) return undefined;
  try {
    const obj = JSON.parse(raw) as Entry<T>;
    if (Date.now() > obj.exp) {
      sessionStorage.removeItem(key);
      return undefined;
    }
    return obj.value;
  } catch {
    sessionStorage.removeItem(key);
    return undefined;
  }
}

export function scClear(prefix?: string): void {
  if (!prefix) return sessionStorage.clear();
  for (const k of Object.keys(sessionStorage)) {
    if (k.startsWith(prefix)) sessionStorage.removeItem(k);
  }
}
