import React from "react";
import { createRoot } from "react-dom/client";
import Workbench from "./Workbench";
import "./style.css";
createRoot(document.getElementById("root")).render(
  <Workbench config={window.APP_CONFIG} />,
);
