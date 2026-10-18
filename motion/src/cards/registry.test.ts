import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { LocalizationError } from "../localization";
import { SUPPORTED_LOCALES } from "../localization/language-config";
import { fitPhrase } from "../typography/fitPhrase";
import { theme } from "../themes/tokens";
import { CARD_IDS, CARD_REGISTRY, getAvailableCards } from "./registry";

describe("getAvailableCards", () => {
  for (const locale of SUPPORTED_LOCALES) {
    it(`returns every card for ${locale}`, () => {
      const cards = getAvailableCards(locale);
      assert.equal(cards.length, 25);
      assert.deepEqual(cards.map((card) => card.id), [...CARD_IDS]);
      for (const card of cards) {
        assert.ok(card.supportedLocales.includes(locale));
        assert.ok(card.requiredData);
        assert.ok(card.optionalData);
        assert.ok(card.variants.length > 0);
      }
    });
  }

  it("rejects an unsupported locale", () => {
    assert.throws(() => getAvailableCards("fr-FR"), LocalizationError);
  });
});

describe("card registry", () => {
  it("registers all 25 cards for the three project languages", () => {
    assert.equal(CARD_REGISTRY.length, 25);
    for (const card of CARD_REGISTRY) {
      assert.deepEqual([...card.supportedLocales], [...SUPPORTED_LOCALES]);
      assert.ok(card.requiredKeys.length > 0);
    }
  });
});

describe("AutoFitText locales", () => {
  it("keeps English words whole", () => {
    const layout = fitPhrase({ text: "Planning to buy property?", locale: "en-US", maxWidth: 860, maxHeight: 640, role: theme.type.hook });
    assert.equal(layout.overflow, false);
    assert.deepEqual(layout.lines.flat(), ["Planning", "to", "buy", "property?"]);
  });

  it("keeps Russian words whole", () => {
    const layout = fitPhrase({ text: "Планируете купить недвижимость?", locale: "ru-RU", maxWidth: 860, maxHeight: 640, role: theme.type.hook });
    assert.equal(layout.overflow, false);
    assert.deepEqual(layout.lines.flat(), ["Планируете", "купить", "недвижимость?"]);
  });

  it("wraps Chinese without inserting spaces", () => {
    const text = "打算买房吗？";
    const layout = fitPhrase({ text, locale: "zh-CN", maxWidth: 860, maxHeight: 640, role: theme.type.hook });
    assert.equal(layout.overflow, false);
    assert.equal(layout.lines.flat().join(""), text);
  });
});
