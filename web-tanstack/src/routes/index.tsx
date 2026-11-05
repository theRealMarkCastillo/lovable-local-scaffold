import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import Workbench from "../shared/Workbench";
import { getPublicConfig, checkBackend } from "../server-functions";
export const Route = createFileRoute("/")({
  loader: async () => ({ config: await getPublicConfig() }),
  component: Home,
});
function Home() {
  const { config } = Route.useLoaderData();
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  async function check() {
    setBusy(true);
    try {
      const data = await checkBackend();
      setStatus(
        data.anonymousAccess === "denied"
          ? "Server backend reachable · anonymous access denied"
          : `Server backend reachable · anonymous rows: ${data.anonymousRows}`,
      );
    } catch {
      setStatus("Server backend unavailable. Check the local stack.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <aside className="server-demo" aria-label="Server rendering example">
        <strong>TanStack Start · rendered by the Node server</strong>
        <button className="secondary" disabled={busy} onClick={check}>
          Check server connection
        </button>
        <span role="status">{status}</span>
      </aside>
      <Workbench config={config} />
    </>
  );
}
