import {existsSync} from "node:fs";
import path from "node:path";
import {Config} from "@remotion/cli/config";
import {ensureStore, motionStore} from "./store-path";

Config.setOverwriteOutput(true);
Config.setVideoImageFormat("png");

const store = ensureStore();
const publicDir = path.join(store, "public");
const bundledPublic = path.resolve("public");
if (existsSync(publicDir) && motionStore() !== path.resolve("output")) {
  Config.setPublicDir(publicDir);
} else if (existsSync(bundledPublic)) {
  Config.setPublicDir(bundledPublic);
}
