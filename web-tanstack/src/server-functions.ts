import { createServerFn } from "@tanstack/react-start";

// Only this explicit public projection is serialized into the SSR document.
// Never return process.env, a service key, or an internal connection URL.
export const getPublicConfig = createServerFn({ method: "GET" }).handler(
  async () => {
    const supabaseUrl = process.env.SUPABASE_BROWSER_URL;
    const supabaseKey = process.env.SUPABASE_BROWSER_KEY;
    const publicUrl = process.env.PUBLIC_URL;
    if (!supabaseUrl || !supabaseKey || !publicUrl)
      throw new Error("Missing public app configuration");
    return { supabaseUrl, supabaseKey, publicUrl };
  },
);

// Public read-only connectivity example. It uses the anon role so RLS still applies.
// This does not authenticate a user or grant access to their private notes.
export const checkBackend = createServerFn({ method: "GET" }).handler(
  async () => {
    const url = process.env.SUPABASE_SERVER_URL;
    const key = process.env.SUPABASE_BROWSER_KEY;
    if (!url || !key) throw new Error("Missing server backend configuration");
    const response = await fetch(
      url.replace(/\/$/, "") + "/rest/v1/notes?select=id&limit=1",
      {
        headers: { apikey: key, Authorization: `Bearer ${key}` },
        signal: AbortSignal.timeout(5000),
      },
    );
    if (response.status === 401 || response.status === 403)
      return {
        reachable: true,
        anonymousAccess: "denied" as const,
        anonymousRows: 0,
      };
    if (!response.ok)
      throw new Error("Server could not reach the database API");
    const rows = await response.json();
    return {
      reachable: true,
      anonymousAccess: "filtered" as const,
      anonymousRows: rows.length as number,
    };
  },
);
