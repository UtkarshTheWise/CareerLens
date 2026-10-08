import { registerHooks } from "node:module";
import { existsSync } from "node:fs";
import { extname } from "node:path";
// Match the application's TypeScript bundler resolution for extensionless local imports.
// Node 22.16+ runs the actual source; no compiler service or Windows account lookup is needed.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier.startsWith(".") && !extname(specifier) && context.parentURL) {
      const source = new URL(`${specifier}.ts`, context.parentURL);
      if (existsSync(source)) return nextResolve(source.href, context);
    }
    return nextResolve(specifier, context);
  },
});
