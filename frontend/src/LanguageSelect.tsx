import { Globe } from 'lucide-react';
import type { Lang } from './types';
import { readLanguage, translate } from './locale';

export function LanguageSelect({ lang, onChange, className = '' }: { lang: Lang; onChange: (lang: Lang) => void; className?: string }) {
  return <label className={`locale-select ${className}`}>
    <Globe size={17} aria-hidden="true" />
    <select aria-label={translate(lang, 'Interface language', '界面语言')} value={lang} onChange={e => onChange(readLanguage(e.target.value))}>
      <option value="en" lang="en">English</option>
      <option value="zh" lang="zh">中文</option>
      <option value="ru" lang="ru">Русский</option>
    </select>
  </label>;
}
