import { mkdir, copyFile } from "node:fs/promises";
await mkdir(new URL("../src/shared/", import.meta.url), { recursive: true });
for (const file of ["Workbench.jsx", "style.css", "session-state.js"])
  await copyFile(
    new URL("../../web/src/" + file, import.meta.url),
    new URL("../src/shared/" + file, import.meta.url),
  );
