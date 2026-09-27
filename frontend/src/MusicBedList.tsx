import type {Lang} from './types';
import {bedControlDisabled, candidateControlDisabled, formatClock} from './musicBed';

export type BedTrack = {
  key: string;
  title: string;
  artist: string;
  mood: string;
  duration: number;
  origin: 'curated' | 'uploaded';
  available: boolean;
  license?: string;
};

const text = (lang: Lang, ru: string, en: string, zh: string) => lang === 'ru' ? ru : lang === 'zh' ? zh : en;

const moodLabel = (lang: Lang, mood: string) => ({
  calm: text(lang, 'Спокойное', 'Calm', '舒缓'),
  uplifting: text(lang, 'Позитивное', 'Uplifting', '轻快'),
  energetic: text(lang, 'Энергичное', 'Energetic', '活力'),
  acoustic: text(lang, 'Акустика', 'Acoustic', '原声'),
  other: text(lang, 'Другое', 'Other', '其他'),
} as Record<string, string>)[mood] || text(lang, 'Другое', 'Other', '其他');

function meta(lang: Lang, track: BedTrack) {
  return [moodLabel(lang, track.mood), formatClock(track.duration), track.artist, track.license].filter(Boolean).join(' · ');
}

export function MusicBedList({lang, tracks, selectedKey, group, onSelect}:{lang:Lang; tracks:BedTrack[]; selectedKey:string; group:string; onSelect:(key:string)=>void}) {
  if (!tracks.length) return <p>{text(lang, 'В этом разделе пока нет композиций.', 'No tracks in this section yet.', '此分类暂无曲目。')}</p>;
  return <div className="music-bed-list" role="radiogroup" aria-label={text(lang, 'Композиции', 'Tracks', '曲目')}>{tracks.map(track => {
    const selected = selectedKey === track.key;
    return <div className={selected ? 'music-bed-item is-selected' : 'music-bed-item'} key={track.key}>
      <label className={selected ? 'music-bed-row is-selected' : 'music-bed-row'}>
        <input type="radio" name={group} value={track.key} checked={selected} disabled={bedControlDisabled(track.available)} onChange={() => onSelect(track.key)}/>
        <span className="music-bed-copy"><strong>{track.title}</strong><small>{track.available ? meta(lang, track) : text(lang, 'Файл пока недоступен', 'File not available yet', '文件暂不可用')}</small></span>
        {selected && <span className="music-bed-badge">{text(lang, 'Выбрано', 'Selected', '已选择')}</span>}
      </label>
      {selected && track.available && <audio controls preload="none" aria-label={text(lang, 'Прослушать ', 'Preview ', '试听 ') + track.title} src={`/api/studio/soundtracks/${encodeURIComponent(track.key)}/media`}/>}
    </div>;
  })}</div>;
}

export function MusicCandidateList({lang, tracks, chosenIds, busyKey, assetIdFor, onToggle}:{lang:Lang; tracks:BedTrack[]; chosenIds:string[]; busyKey:string; assetIdFor:(key:string)=>string|null; onToggle:(key:string, on:boolean)=>void}) {
  return <div className="music-candidate-list">
    <p>{text(lang, 'Отмечено для сравнения', 'Checked for comparison', '已勾选用于比较')} · {chosenIds.length}/3</p>
    {tracks.map(track => {
      const assetId = assetIdFor(track.key);
      const checked = !!assetId && chosenIds.includes(assetId);
      return <label className={checked ? 'music-candidate is-checked' : 'music-candidate'} key={track.key}>
        <input type="checkbox" value={track.key} checked={checked} disabled={candidateControlDisabled({busy: busyKey === track.key, checked, chosen: chosenIds.length, available: track.available})} onChange={event => onToggle(track.key, event.target.checked)}/>
        <span className="music-bed-copy"><strong>{track.title}</strong><small>{meta(lang, track)}</small></span>
      </label>;
    })}
  </div>;
}
