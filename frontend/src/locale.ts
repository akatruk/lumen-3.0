import type { Lang, ContentLang } from './types';
import { ru } from './ru';

export function contentLanguage(lang: Lang): ContentLang { return lang === 'zh' ? 'zh' : 'en'; }
export function readLanguage(value: string | null): Lang { return value === 'ru' || value === 'zh' ? value : 'en'; }
export function translate(lang: Lang, en: string, zh: string): string {
  return lang === 'ru' ? (ru[en] ?? en) : lang === 'zh' ? zh : en;
}
export function translateRecord<T extends Record<string, string>>(lang: Lang, en: T, zh: Record<keyof T, string>): T {
  return Object.fromEntries(Object.keys(en).map(key => [key, translate(lang, en[key], zh[key])])) as T;
}
