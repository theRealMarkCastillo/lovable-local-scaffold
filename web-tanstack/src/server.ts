import { randomBytes } from "node:crypto";
import {
  createStartHandler,
  defaultStreamHandler,
} from "@tanstack/react-start/server";
const handler = createStartHandler(defaultStreamHandler);
export default {
  async fetch(request: Request) {
    if (new URL(request.url).pathname === "/health") return new Response("ok");
    const nonce = randomBytes(18).toString("base64");
    // Nitro supplies a fetch-compatible request; preserve it rather than cloning
    // it with Node's different Request implementation. This header is internal.
    request.headers.set("x-csp-nonce", nonce);
    const response = await handler(request);
    response.headers.set(
      "Content-Security-Policy",
      `default-src 'self'; script-src 'self' 'nonce-${nonce}'; style-src 'self'; connect-src 'self' https: wss:; img-src 'self' blob: data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`,
    );
    response.headers.set("Cache-Control", "private, no-store");
    response.headers.set("X-Content-Type-Options", "nosniff");
    response.headers.set("Referrer-Policy", "same-origin");
    return response;
  },
};
