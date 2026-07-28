import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app";
import { PagesDemo } from "./features/pages/PagesDemo";
import "./styles/app.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {import.meta.env.VITE_PUBLIC_DEMO === "true" ? <PagesDemo /> : <App />}
  </StrictMode>
);
