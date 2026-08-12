/// <reference types="vitest/config" />
import { defineConfig } from "vite";

// Tauri v2's recommended dev-server contract: a fixed, non-negotiable port
// (Rust's `devUrl` in tauri.conf.json points at it) and ignoring src-tauri/
// so a `cargo build` output doesn't trigger a frontend rebuild loop.
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
