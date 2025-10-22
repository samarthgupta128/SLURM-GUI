/**
 * Helper function to build API URLs
 * When using Vite's proxy, we use relative URLs
 */
export const buildApiUrl = (path: string): string => {
  return path.startsWith('/') ? path : `/${path}`;
};