import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "./",
  // Tailwind runs through @tailwindcss/vite. An inline (empty) PostCSS config stops Vite from walking up
  // the directory tree and picking up an unrelated postcss.config.* outside this repository.
  css: { postcss: {} },
  build: {
    rolldownOptions: {
      input: {
        sidepanel: resolve(import.meta.dirname, "sidepanel.html"),
        options: resolve(import.meta.dirname, "options.html"),
        background: resolve(import.meta.dirname, "src/background.ts"),
      },
      output: {
        entryFileNames: (chunk) =>
          chunk.name === "background"
            ? "background.js"
            : "assets/[name]-[hash].js",
      },
    },
  },
});
