import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

function filesUnder(dir: string): string[] {
  const found: string[] = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) found.push(...filesUnder(path));
    else if (/\.(ts|tsx)$/.test(name) && !name.endsWith(".test.ts")) found.push(path);
  }
  return found;
}

describe("frame-driven timing", () => {
  it("does not use random or wall-clock timing", () => {
    const src = fileURLToPath(new URL("..", import.meta.url));
    const banned = ["Math.random(", "Date.now(", "setTimeout(", "setInterval("];
    for (const path of filesUnder(src)) {
      const source = readFileSync(path, "utf8");
      for (const token of banned) {
        assert.equal(source.includes(token), false, `${path} contains ${token}`);
      }
    }
  });
});
