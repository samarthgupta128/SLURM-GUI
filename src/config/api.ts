/**
 * Helper function to build API URLs
 * When using Vite's proxy, we use relative URLs
 */
// Try multiple base URLs to support running backend in Docker or locally.
const CANDIDATE_BASES = [
  '', // relative (Vite proxy)
  'http://host.docker.internal:8001',
  'http://localhost:8001'
];

let resolvedBase: string | null = null;

const testUrl = async (base: string, path: string) => {
  const url = base ? `${base}${path.startsWith('/') ? path : `/${path}`}` : (path.startsWith('/') ? path : `/${path}`);
  try {
    const resp = await fetch(url, { method: 'GET', headers: { Accept: 'application/json' } });
    if (!resp.ok) return false;
    const txt = await resp.text();
    JSON.parse(txt);
    return true;
  } catch (e) {
    return false;
  }
};

// Resolve the base once at runtime.
export const resolveApiBase = async (path = '/api/resources') => {
  if (resolvedBase !== null) return resolvedBase;
  for (const base of CANDIDATE_BASES) {
    // eslint-disable-next-line no-await-in-loop
    const ok = await testUrl(base, path);
    if (ok) {
      resolvedBase = base;
      return resolvedBase;
    }
  }
  // Fallback to relative
  resolvedBase = '';
  return resolvedBase;
};

export const buildApiUrl = (path: string) => {
  // If resolvedBase is set, use it; otherwise return the relative path and rely on the resolver to be run first
  return resolvedBase !== null ? (resolvedBase ? `${resolvedBase}${path.startsWith('/') ? path : `/${path}`}` : (path.startsWith('/') ? path : `/${path}`)) : (path.startsWith('/') ? path : `/${path}`);
};
