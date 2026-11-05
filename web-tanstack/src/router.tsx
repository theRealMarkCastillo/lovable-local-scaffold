import { createRouter } from "@tanstack/react-router";
import { createIsomorphicFn } from "@tanstack/react-start";
import { getRequestHeader } from "@tanstack/react-start/server";
import { routeTree } from "./routeTree.gen";
const nonce = createIsomorphicFn()
  .server(() => getRequestHeader("x-csp-nonce"))
  .client(() => undefined);
export function getRouter() {
  return createRouter({
    routeTree,
    scrollRestoration: true,
    ssr: { nonce: nonce() },
  });
}
declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof getRouter>;
  }
}
