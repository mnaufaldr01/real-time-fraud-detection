import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, path.resolve(__dirname, ".."), "");
  const rootEnvDemo = loadEnv(mode, __dirname, "");
  const analyticsPort = rootEnv.ANALYTICS_API_PORT ?? "8001";
  const proxyTarget =
    process.env.VITE_API_PROXY ?? rootEnv.VITE_API_PROXY ?? `http://localhost:${analyticsPort}`;
  const base =
    process.env.VITE_BASE_PATH ?? rootEnv.VITE_BASE_PATH ?? rootEnvDemo.VITE_BASE_PATH ?? "/";

  return {
    base,
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
