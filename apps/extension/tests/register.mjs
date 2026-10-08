import {registerHooks} from "node:module";import {existsSync} from "node:fs";import {fileURLToPath} from "node:url";
registerHooks({resolve(specifier,context,next){if(specifier.startsWith(".")&&!/\.[cm]?[jt]s$/.test(specifier)){const url=new URL(specifier+".ts",context.parentURL);if(existsSync(fileURLToPath(url)))return next(url.href,context);}return next(specifier,context);}});
