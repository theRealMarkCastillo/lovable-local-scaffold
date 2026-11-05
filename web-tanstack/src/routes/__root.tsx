import {
  createRootRoute,
  HeadContent,
  Outlet,
  Scripts,
} from "@tanstack/react-router";
import type { ReactNode } from "react";
import css from "../shared/style.css?url";
export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Local Supabase · TanStack Start" },
    ],
    links: [{ rel: "stylesheet", href: css }],
  }),
  component: () => <Outlet />,
  shellComponent: Shell,
  notFoundComponent: () => (
    <main>
      <h1>Page not found</h1>
      <a href="/">Return to workbench</a>
    </main>
  ),
});
function Shell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}
