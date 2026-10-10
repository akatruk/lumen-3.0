import { LocalizationError } from "../localization";
import { isSupportedLocale, SUPPORTED_LOCALES, type SupportedLocale } from "../localization/language-config";

export const CARD_IDS = [
  "kinetic_hook",
  "big_number",
  "property_price",
  "rental_yield",
  "roi",
  "cash_flow",
  "property_comparison",
  "buy_vs_rent",
  "progress_steps",
  "document_check",
  "property_features",
  "location",
  "amenities",
  "timeline",
  "before_after",
  "checklist",
  "stat_reveal",
  "quote",
  "cta",
  "caption_card",
  "property_listing",
  "investment_card",
  "location_card",
  "legal_card",
  "key_takeaway",
] as const;

export type CardId = (typeof CARD_IDS)[number];

const KEYS: Record<CardId, readonly string[]> = {
  kinetic_hook: ["hook.buy"],
  big_number: ["process.steps"],
  property_price: ["realEstate.price", "comparison.before", "comparison.after"],
  rental_yield: ["realEstate.rentalYield", "realEstate.propertyValue", "realEstate.monthlyRent", "realEstate.annualRent"],
  roi: ["realEstate.roi", "roi.investment", "roi.return"],
  cash_flow: ["realEstate.cashFlow", "cashFlow.income", "cashFlow.expenses", "cashFlow.net"],
  property_comparison: ["comparison.versus", "comparison.propertyA", "comparison.propertyB", "realEstate.price", "realEstate.size", "realEstate.location", "realEstate.yield", "realEstate.fees", "places.bangkok"],
  buy_vs_rent: ["comparison.buy", "comparison.rent"],
  progress_steps: ["process.step", "process.search", "process.viewing", "process.offer", "process.contract", "process.handover"],
  document_check: ["realEstate.documents", "document.verified", "document.approved", "document.review"],
  property_features: ["realEstate.property", "features.bedrooms", "features.bathrooms", "features.area", "features.floor", "features.parking", "features.balcony"],
  location: ["realEstate.location", "location.distance", "realEstate.transport", "location.school", "location.shopping", "location.park"],
  amenities: ["realEstate.amenities", "features.pool", "features.gym", "features.parking", "features.balcony"],
  timeline: ["process.step", "process.search", "process.contract", "process.handover"],
  before_after: ["comparison.before", "comparison.after"],
  checklist: ["checklist.title", "checklist.inspection", "checklist.documents", "checklist.approval"],
  stat_reveal: ["realEstate.occupancy", "stat.support"],
  quote: ["quote.line"],
  cta: ["cta.learnMore", "cta.contactUs", "cta.bookConsultation", "cta.seeProperties", "cta.startSearch"],
  caption_card: ["stress.management", "stress.mortgage"],
  property_listing: ["realEstate.condominium", "places.bangkok", "realEstate.yield"],
  investment_card: ["realEstate.investment", "realEstate.purchasePrice", "realEstate.monthlyRent", "realEstate.annualIncome", "realEstate.yield", "realEstate.roi"],
  location_card: ["places.bangkok", "realEstate.location", "location.score", "realEstate.transport", "location.distance", "realEstate.amenities"],
  legal_card: ["realEstate.documents", "document.status", "document.verification", "document.risk", "realEstate.approval"],
  key_takeaway: ["stress.international"],
};

const FIELDS: Record<CardId, { requiredData: readonly string[]; optionalData: readonly string[]; variants: readonly string[] }> = {
  kinetic_hook: { requiredData: ["text"], optionalData: ["emphasis"], variants: ["word_pop", "rapid_reveal", "scale_punch", "slide_stack"] },
  big_number: { requiredData: ["value"], optionalData: ["label"], variants: ["count_up", "scale_in", "impact", "minimal"] },
  property_price: { requiredData: ["price", "currency"], optionalData: ["previous"], variants: ["standard"] },
  rental_yield: { requiredData: ["yieldPercent", "currency"], optionalData: ["value", "monthlyRent", "annualRent"], variants: ["standard"] },
  roi: { requiredData: ["roiPercent", "currency"], optionalData: ["investment", "returnAmount"], variants: ["standard"] },
  cash_flow: { requiredData: ["income", "expenses", "currency"], optionalData: [], variants: ["standard"] },
  property_comparison: { requiredData: ["price", "currency"], optionalData: ["area", "yieldPercent", "fees"], variants: ["standard"] },
  buy_vs_rent: { requiredData: [], optionalData: ["left", "right"], variants: ["standard"] },
  progress_steps: { requiredData: ["steps"], optionalData: [], variants: ["horizontal", "vertical", "path", "progress_fill"] },
  document_check: { requiredData: [], optionalData: ["status"], variants: ["standard"] },
  property_features: { requiredData: ["bedrooms", "bathrooms", "area"], optionalData: ["floor"], variants: ["standard"] },
  location: { requiredData: ["distanceKm"], optionalData: [], variants: ["standard"] },
  amenities: { requiredData: [], optionalData: ["items"], variants: ["standard"] },
  timeline: { requiredData: ["dates"], optionalData: [], variants: ["vertical", "horizontal", "center_line", "scroll"] },
  before_after: { requiredData: ["previous", "price", "currency"], optionalData: [], variants: ["standard"] },
  checklist: { requiredData: ["items"], optionalData: [], variants: ["stack", "rapid", "minimal", "progressive"] },
  stat_reveal: { requiredData: ["occupancy"], optionalData: [], variants: ["impact", "counter", "comparison", "scale"] },
  quote: { requiredData: ["text"], optionalData: [], variants: ["editorial", "pull"] },
  cta: { requiredData: [], optionalData: ["actions"], variants: ["standard"] },
  caption_card: { requiredData: ["text"], optionalData: ["support"], variants: ["standard"] },
  property_listing: { requiredData: ["price", "currency"], optionalData: ["area", "bedrooms", "yieldPercent"], variants: ["standard"] },
  investment_card: { requiredData: ["price", "currency"], optionalData: ["monthlyRent", "annualRent", "yieldPercent", "roiPercent"], variants: ["standard"] },
  location_card: { requiredData: ["score"], optionalData: [], variants: ["standard"] },
  legal_card: { requiredData: [], optionalData: ["status"], variants: ["standard"] },
  key_takeaway: { requiredData: ["text"], optionalData: [], variants: ["standard"] },
};

export type CardDefinition = {
  id: CardId;
  supportedLocales: readonly SupportedLocale[];
  requiredKeys: readonly string[];
  requiredData: readonly string[];
  optionalData: readonly string[];
  variants: readonly string[];
};

export const CARD_REGISTRY: readonly CardDefinition[] = CARD_IDS.map((id) => ({
  id,
  supportedLocales: SUPPORTED_LOCALES,
  requiredKeys: KEYS[id],
  requiredData: FIELDS[id].requiredData,
  optionalData: FIELDS[id].optionalData,
  variants: FIELDS[id].variants,
}));

export function lookupCard(id: string): CardDefinition | undefined {
  return CARD_REGISTRY.find((card) => card.id === id);
}

/** Cards the director may use for this project language. An unknown locale returns nothing. */
export function getAvailableCards(locale: string): readonly CardDefinition[] {
  if (!isSupportedLocale(locale)) {
    throw new LocalizationError(`unsupported locale: ${locale}`);
  }
  return CARD_REGISTRY.filter((card) => card.supportedLocales.includes(locale));
}
