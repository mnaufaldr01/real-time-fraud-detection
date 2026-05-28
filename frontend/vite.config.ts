import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, path.resolve(__dirname, ".."), "");
  const analyticsPort = rootEnv.ANALYTICS_API_PORT ?? "8001";
  const proxyTarget =
    process.env.VITE_API_PROXY ?? rootEnv.VITE_API_PROXY ?? `http://localhost:${analyticsPort}`;

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true,
        },
        "/health": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
