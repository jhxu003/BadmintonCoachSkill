import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    // GitHub Pages serves project sites from /<repository>/ rather than /.
    base: env.VITE_BASE_PATH || "/",
    plugins: [react()],
    server: {
      proxy: {
        "/api": "http://127.0.0.1:8000"
      }
    }
  };
});
