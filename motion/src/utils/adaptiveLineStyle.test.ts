import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  adaptiveLineStyle,
  contrastRatio,
  parseColor,
  pathFromSvgCommands,
  relativeLuminance,
  sampleBackgroundAlongPath,
  sceneThemeFromPlate,
} from "./adaptiveLineStyle";

const GOLD = "#E0B15A";
const BEIGE = "#F4EFE6";
const INK = "#12110F";

describe("adaptiveLineStyle contrast math", () => {
  it("parses hex and computes luminance", () => {
    const gold = parseColor(GOLD)!;
    const beige = parseColor(BEIGE)!;
    assert.ok(relativeLuminance(beige) > relativeLuminance(gold));
    assert.ok(contrastRatio(gold, beige) < 3, "gold on beige must fail graphics threshold");
  });

  it("samples the full path not only endpoints on a gradient", () => {
    const path = [
      { x: 0, y: 0 },
      { x: 50, y: 0 },
      { x: 100, y: 0 },
    ];
    const colors = sampleBackgroundAlongPath(
      {
        kind: "gradient",
        stops: [
          { offset: 0, color: INK },
          { offset: 0.5, color: BEIGE },
          { offset: 1, color: BEIGE },
        ],
      },
      path,
    );
    assert.equal(colors.length, path.length);
    // Mid/end must be light — endpoint-only would miss mid-path beige failure.
    assert.ok(relativeLuminance(colors[1]) > 0.5);
    assert.ok(relativeLuminance(colors[2]) > 0.5);
  });

  it("outlines or recolors gold on beige paper (V11.2 connector bug)", () => {
    const path = pathFromSvgCommands("M40 60 C 120 20, 240 20, 320 60");
    const style = adaptiveLineStyle({
      background: BEIGE,
      path,
      preferredColor: GOLD,
      strokeWidth: 4,
      sceneTheme: "paper",
      minContrast: 3,
    });
    assert.notEqual(style.contrastStatus, "ok");
    assert.ok(style.contrastStatus === "outlined" || style.contrastStatus === "recolored");
    if (style.contrastStatus === "outlined") {
      assert.ok(style.outlineColor);
      assert.ok(style.outlineWidth > 0);
      assert.equal(style.strokeColor, GOLD);
    } else {
      assert.notEqual(style.strokeColor.toLowerCase(), GOLD.toLowerCase());
    }
    assert.ok(style.minRatio >= 2.0);
  });

  it("keeps gold on dark ink without outline", () => {
    const style = adaptiveLineStyle({
      background: INK,
      path: [
        { x: 0, y: 0 },
        { x: 100, y: 40 },
        { x: 200, y: 0 },
      ],
      preferredColor: GOLD,
      strokeWidth: 4,
      sceneTheme: "ink",
    });
    assert.equal(style.contrastStatus, "ok");
    assert.equal(style.strokeColor, GOLD);
    assert.equal(style.outlineWidth, 0);
    assert.ok(style.minRatio >= 3);
  });

  it("detects mid-path low contrast when endpoints are dark", () => {
    // Endpoints ink (ok), mid span beige (fail) — classic endpoint-only bug.
    const path = [
      { x: 0, y: 0 },
      { x: 50, y: 0 },
      { x: 100, y: 0 },
    ];
    const style = adaptiveLineStyle({
      background: {
        kind: "samples",
        colors: [INK, BEIGE, INK],
      },
      path,
      preferredColor: GOLD,
      strokeWidth: 3,
      sceneTheme: "auto",
      minContrast: 3,
    });
    assert.notEqual(style.contrastStatus, "ok");
  });

  it("maps plate ids to scene themes", () => {
    assert.equal(sceneThemeFromPlate("paper_grain"), "paper");
    assert.equal(sceneThemeFromPlate("navy_grid"), "navy");
    assert.equal(sceneThemeFromPlate("ink_lift"), "ink");
  });
});
