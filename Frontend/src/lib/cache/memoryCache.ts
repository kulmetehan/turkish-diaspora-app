// Frontend/src/lib/cache/memoryCache.ts
type Entry<T> = { value: T; exp: number };
const store = new Map<string, Entry<unknown>>();

export function mcSet<T>(key: string, value: T, ttlMs: number): void {
  store.set(key, { value, exp: Date.now() + ttlMs });
}
export function mcGet<T>(key: string): T | undefined {
  const hit = store.get(key);
  if (!hit) return undefined;
  if (Date.now() > hit.exp) {
    store.delete(key);
    return undefined;
  }
  return hit.value as T;
}
export function mcClear(): void { store.clear(); }
