import { AbsoluteFill, Sequence } from "remotion";
import { SUPPORTED_LOCALES } from "../localization/language-config";
import { theme } from "../themes/tokens";
import { CardView } from "./CardView";
import { CARD_IDS } from "./registry";

export const CARD_HOLD = 45;

export const MULTILINGUAL_BEATS = CARD_IDS.flatMap((cardId) =>
  SUPPORTED_LOCALES.map((locale) => ({ cardId, locale })),
);

export const MULTILINGUAL_DURATION = MULTILINGUAL_BEATS.length * CARD_HOLD;

export function MultilingualCardShowcase() {
  return (
    <AbsoluteFill style={{ background: theme.color.bg }}>
      {MULTILINGUAL_BEATS.map((beat, index) => (
        <Sequence key={`${beat.cardId}-${beat.locale}`} from={index * CARD_HOLD} durationInFrames={CARD_HOLD} name={`${beat.cardId}-${beat.locale}`}>
          <CardView cardId={beat.cardId} locale={beat.locale} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
