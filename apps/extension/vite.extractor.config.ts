import { defineConfig } from "vite";
import { resolve } from "node:path";
export default defineConfig({
  css: { postcss: {} }, // see vite.config.ts
  build: {
    emptyOutDir: false,
    lib: {
      entry: resolve(import.meta.dirname, "src/extract.ts"),
      name: "CareerLensExtractor",
      formats: ["iife"],
      fileName: () => "extractor.js",
    },
  },
});
