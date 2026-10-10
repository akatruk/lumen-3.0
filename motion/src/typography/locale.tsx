import { createContext, useContext, type ReactNode } from "react";
import type { SupportedLocale } from "../localization/language-config";

const LocaleContext = createContext<SupportedLocale>("en-US");

export function LocaleProvider({ locale, children }: { locale: SupportedLocale; children: ReactNode }) {
  return <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>;
}

export function useLocale(): SupportedLocale {
  return useContext(LocaleContext);
}
