export type Speech = "en-US" | "ru-RU" | "zh-CN";

export type SpeechLine = {
  original?: string;
  zh?: string;
  en?: string;
  ru?: string;
  text?: string;
};

function saved(value: string | null | undefined): Speech | null {
  if (value === "ru" || value === "ru-RU") return "ru-RU";
  if (value === "en" || value === "en-US") return "en-US";
  if (value === "zh" || value === "zh-CN") return "zh-CN";
  return null;
}

function joined(lines: SpeechLine[], key: keyof SpeechLine): string {
  return lines.map((line) => line[key] || "").join(" ");
}

/** Source speech. A translation stored in `en` is not the source. */
export function sourceSpeechLocale(input: {
  sourceLanguage?: string | null;
  lines?: SpeechLine[];
}): Speech | null {
  const stored = saved(input.sourceLanguage);
  if (stored) return stored;
  const lines = input.lines || [];
  const spoken = `${joined(lines, "zh")} ${joined(lines, "original")}`;
  if (/[\u4e00-\u9fff]/.test(spoken)) return "zh-CN";
  if (/[\u0400-\u04ff]/.test(joined(lines, "original"))) return "ru-RU";
  return null;
}

/** Unknown source stays on the original soundtrack. A caption-language change is a dub. */
export function audioMode(source: Speech | null, captions: Speech): "original" | "dub" {
  if (!source || source === captions) return "original";
  return "dub";
}
