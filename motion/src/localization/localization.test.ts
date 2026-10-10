import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { describe, it } from "node:test";
import { CARD_REGISTRY } from "../cards/registry";
import { theme } from "../themes/tokens";
import { fitPhrase } from "../typography/fitPhrase";
import { tokenizeWords } from "../utils/words";
import { GLYPH_SAMPLES, TYPOGRAPHY_PROFILES } from "./fonts";
import { formatCompactCurrency, formatCurrency } from "./formatter";
import { GLOSSARY_IDS, glossaryEntry } from "./glossary";
import { SUPPORTED_LOCALES } from "./language-config";
import { LocalizationError, messageKeys, sameKeysAcrossLocales, t } from "./index";
import { segmentForLineBreak, segmentTextForMotion } from "./segment";
import { validateLocalizedCard } from "./validateLocalizedCard";

const STRESS = {
  "en-US": "International property investment opportunities",
  "ru-RU": "Возможности для международных инвестиций в недвижимость",
  "zh-CN": "国际房地产投资机会",
} as const;

describe("localization", () => {
  it("keeps the same keys in every locale and refuses a silent English fallback", () => {
    sameKeysAcrossLocales();
    assert.ok(messageKeys().includes("realEstate.rentalYield"));
    assert.throws(() => t("zh-CN", "realEstate.missing"), LocalizationError);
    try {
      t("zh-CN", "realEstate.missing");
    } catch (error) {
      assert.equal(String(error).includes("Rental yield"), false);
    }
  });

  it("localizes the glossary in all three languages", () => {
    for (const id of GLOSSARY_IDS) {
      const row = glossaryEntry(id);
      assert.notEqual(row["ru-RU"], row["en-US"]);
      assert.notEqual(row["zh-CN"], row["en-US"]);
    }
    assert.equal(t("ru-RU", "comparison.buy"), "Купить");
    assert.equal(t("zh-CN", "comparison.rent"), "租赁");
  });

  it("formats money in the locale without converting the currency", () => {
    assert.equal(formatCurrency(8_500_000, "THB", "en-US"), "THB 8,500,000");
    assert.match(formatCurrency(8_500_000, "THB", "ru-RU"), /8[\s\u00a0\u202f]500[\s\u00a0\u202f]000 THB/);
    assert.equal(formatCompactCurrency(8_500_000, "THB", "zh-CN"), "THB 850万");
    assert.match(formatCompactCurrency(8_500_000, "THB", "ru-RU"), /млн THB/);
    assert.throws(() => formatCurrency(1, "usd", "en-US"), LocalizationError);
  });

  it("segments Chinese as phrases and keeps Russian words whole", () => {
    const zh = segmentTextForMotion("打算购买房产吗？", "zh-CN");
    assert.deepEqual(zh.join(""), "打算购买房产吗？");
    assert.ok(zh.length > 1);
    assert.deepEqual(segmentTextForMotion("Планируете купить недвижимость?", "ru-RU"), [
      "Планируете",
      "купить",
      "недвижимость?",
    ]);
    const lines = segmentForLineBreak("打算买房吗？");
    assert.equal(lines[0]?.startsWith("？"), false);
    assert.equal(lines.at(-1)?.endsWith("？") || lines.join("").endsWith("？"), true);
  });

  it("fits stress copy without splitting Latin or Cyrillic words", () => {
    for (const locale of SUPPORTED_LOCALES) {
      const text = STRESS[locale];
      const layout = fitPhrase({
        text,
        locale,
        maxWidth: 860,
        maxHeight: 640,
        role: theme.type.hook,
        maxLines: locale === "ru-RU" ? 5 : 4,
      });
      assert.equal(layout.overflow, false, locale);
      if (locale === "zh-CN") {
        assert.equal(layout.lines.flat().join(""), text);
      } else {
        assert.deepEqual(layout.lines.flat(), tokenizeWords(text));
      }
    }
  });

  it("validates every priority card in every locale", () => {
    for (const card of CARD_REGISTRY) {
      assert.deepEqual([...card.supportedLocales], [...SUPPORTED_LOCALES]);
      for (const locale of SUPPORTED_LOCALES) validateLocalizedCard(card.id, locale, { currency: "THB" });
    }
    assert.throws(() => validateLocalizedCard("property_listing", "fr-FR", { currency: "THB" }), LocalizationError);
  });

  it("covers the sample glyphs in the production fonts", () => {
    const latin = TYPOGRAPHY_PROFILES.latin.fontFiles.find((file) => existsSync(file));
    const cjk = TYPOGRAPHY_PROFILES.cjk.fontFiles.find((file) => existsSync(file));
    assert.ok(latin, "Latin/Cyrillic font file");
    assert.ok(cjk, "Simplified Chinese font file");
    const script = `
from fontTools.ttLib import TTCollection, TTFont
import sys
path, text = sys.argv[1], sys.argv[2]
fonts = TTCollection(path).fonts if path.endswith(".ttc") else [TTFont(path)]
needed = {ord(ch) for ch in text}
ok = False
for font in fonts:
    cmap = font.getBestCmap() or {}
    if needed <= set(cmap):
        ok = True
        break
sys.exit(0 if ok else 1)
`;
    execFileSync("python3", ["-c", script, latin, GLYPH_SAMPLES["en-US"] + GLYPH_SAMPLES["ru-RU"]], { stdio: "pipe" });
    execFileSync("python3", ["-c", script, cjk, GLYPH_SAMPLES["zh-CN"]], { stdio: "pipe" });
  });
});
