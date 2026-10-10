import type { SupportedLocale } from "../localization/language-config";
import type { TypeRole } from "../themes/tokens";
import { estimateWidth } from "../utils/measure";
import { layoutText, type Measure, type TextLayout } from "../utils/textLayout";

export function fitPhrase(options: {
  text: string;
  maxWidth: number;
  maxHeight: number;
  role: TypeRole;
  wrapMode?: "auto" | "word";
  measure?: Measure;
  locale?: SupportedLocale;
  maxLines?: number;
}): TextLayout {
  const measure =
    options.measure ??
    ((text: string, fontSize: number) => estimateWidth(text, fontSize, options.role.weight, options.role.tracking));
  return layoutText({
    text: options.text,
    maxWidth: options.maxWidth,
    maxHeight: options.maxHeight,
    minFontSize: options.role.min,
    maxFontSize: options.role.max,
    lineHeight: options.role.lineHeight,
    wrapMode: options.wrapMode,
    measure,
    locale: options.locale,
    maxLines: options.maxLines,
  });
}
