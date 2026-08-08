import { defineConfig } from "vite";

// TE-002 PoC — minimal Vite config, standard Tauri v2 conventions
// (fixed dev port, ignore src-tauri from the watcher).
export default defineConfig({
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
  test: {
    environment: "jsdom",
  },
});
