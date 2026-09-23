import { useEffect, useState } from "react";
import { translate } from "./locale";
import type { Lang } from "./types";

type Signal = { views: number; likes: number; comments: number; shares: number };
type Concept = {
  id: string;
  kind: string;
  chosen: boolean;
  title: string;
  hook: string;
  story: string;
  characters: string;
  scenes: string[];
  dialogue: string;
  shots: string;
  duration: number;
  editing_style: string;
  relation: string;
  risks: string[];
  script: string;
};
type Dna = {
  why: string;
  narrative: string;
  slots: string[];
  hook: string;
  setup: string;
  conflict: string;
  surprise: string;
  punchline: string;
  pacing: string;
  camera: string;
  editing_rhythm: string;
  text_overlay: string;
  audio_role: string;
  risks: string[];
  observed_caption: string;
};
type Item = {
  id: string;
  source: string;
  url: string;
  creator: string;
  published_at: number;
  duration: number;
  caption: string;
  hashtags: string;
  audio: string;
  category: string;
  sample: boolean;
  score: number;
  signals: Signal[];
  dna?: Dna | null;
  concepts?: Concept[];
};
type Sample = {
  key: string;
  source: string;
  creator: string;
  caption: string;
  category: string;
  duration: number;
  score: number;
  note: string;
  published_at: number;
};
type Handoff = { concept_id: string; title: string; script: string; trend: string };

async function call(path: string, init?: RequestInit) {
  const response = await fetch("/api/trends" + path, { credentials: "same-origin", ...init });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "request_failed");
  return data;
}

const age = (published: number) => {
  const hours = Math.max(0, (Date.now() / 1000 - published) / 3600);
  if (hours < 48) return `${Math.max(1, Math.round(hours))}h`;
  return `${Math.round(hours / 24)}d`;
};

export function Trends({
  lang,
  trendId,
  onOpen,
  onBack,
  onCreate,
}: {
  lang: Lang;
  trendId: string | null;
  onOpen: (id: string) => void;
  onBack: () => void;
  onCreate: (handoff: Handoff) => void;
}) {
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const [items, setItems] = useState<Item[]>([]);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [detail, setDetail] = useState<Item | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    url: "",
    creator: "",
    published_at: new Date(Date.now() - 3600_000).toISOString().slice(0, 16),
    duration: "15",
    caption: "",
    hashtags: "",
    audio: "",
    category: "general",
    views: "0",
    likes: "0",
    comments: "0",
    shares: "0",
  });

  async function loadList() {
    const data = await call("");
    setItems(data.items);
    setSamples(data.samples);
  }
  useEffect(() => {
    let live = true;
    setError("");
    if (!trendId) {
      setDetail(null);
      loadList().catch((e) => live && setError((e as Error).message));
      return;
    }
    call("/" + trendId)
      .then((row) => live && setDetail(row))
      .catch((e) => live && setError((e as Error).message));
    return () => {
      live = false;
    };
  }, [trendId]);

  async function act(path: string, body?: unknown) {
    setBusy(true);
    setError("");
    try {
      const row = await call(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : { method: "POST" });
      if (row.id) {
        setDetail(row);
        onOpen(row.id);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function saveManual(event: React.FormEvent) {
    event.preventDefault();
    await act("/manual", {
      ...form,
      published_at: new Date(form.published_at).getTime() / 1000,
      duration: Number(form.duration),
      views: Number(form.views),
      likes: Number(form.likes),
      comments: Number(form.comments),
      shares: Number(form.shares),
    });
  }

  if (trendId) {
    const row = detail;
    return (
      <div className="page trends-page">
        <button className="text-button" onClick={onBack}>{t("All trends", "全部趋势")}</button>
        {error && <p role="alert" className="error-box">{error}</p>}
        {!row ? <p>{t("Loading trend…", "正在加载趋势…")}</p> : (
          <>
            <header className="director-intro">
              <span className="eyebrow">{row.source} · {row.category}{row.sample ? " · sample" : ""}</span>
              <h1>{row.creator}</h1>
              <p>{row.caption || t("No caption saved.", "未保存文案。")}</p>
            </header>
            <div className="trend-meta">
              <span>{t("Score", "分数")} {row.score}</span>
              <span>{age(row.published_at)}</span>
              <span>{row.signals.at(-1)?.views ?? 0} {t("views", "次观看")}</span>
              <span>{Math.round(row.duration)}s</span>
              {row.audio && <span>{row.audio}</span>}
            </div>
            <p className="director-note">{t("The reference file stays at its URL. Lumen does not download it.", "参考文件留在原链接。Lumen 不会下载它。")}</p>
            <div className="trend-actions">
              <button className="secondary" disabled={busy} onClick={() => void act("/" + row.id + "/analyze")}>{t("Analyze", "分析")}</button>
              <button className="secondary" disabled={busy || !row.dna} onClick={() => void act("/" + row.id + "/concepts")}>{t("Generate parody", "生成变体")}</button>
            </div>
            {row.dna && (
              <section className="director-card">
                <h2>{t("Why it works", "为什么有效")}</h2>
                <p>{row.dna.why}</p>
                <p><strong>{row.dna.narrative}</strong></p>
                <ul className="trend-slots">{row.dna.slots.map((slot) => <li key={slot}>{slot}</li>)}</ul>
                <p>{row.dna.hook}</p>
                <p>{row.dna.editing_rhythm}</p>
                <p>{row.dna.text_overlay}</p>
                {row.dna.risks.map((risk) => <p key={risk}>{risk}</p>)}
              </section>
            )}
            {!!row.concepts?.length && (
              <section className="trend-grid">
                {row.concepts.map((concept) => (
                  <article key={concept.id} className="trend-card">
                    <span className="eyebrow">{concept.kind}</span>
                    <h3>{concept.title}</h3>
                    <p>{concept.story}</p>
                    <p>{concept.relation}</p>
                    <button className="secondary" disabled={busy} onClick={() => void act(`/${row.id}/concepts/${concept.id}/choose`)}>{concept.chosen ? t("Chosen", "已选择") : t("Use this version", "使用此版本")}</button>
                    {concept.chosen && <button className="primary" onClick={() => onCreate({ concept_id: concept.id, title: concept.title, script: concept.script, trend: row.creator })}>{t("Create with Lumen", "用 Lumen 创建")}</button>}
                  </article>
                ))}
              </section>
            )}
          </>
        )}
      </div>
    );
  }

  return (
    <div className="page trends-page">
      <header className="director-intro">
        <span className="eyebrow">LUMEN / TRENDS</span>
        <h1>{t("Find a structure. Then tell your own story.", "先看结构，再讲自己的故事。")}</h1>
        <p>{t("Trends sit in front of Studio. You still upload your footage and approve every edit.", "趋势在 Studio 之前。你仍然上传自己的素材，并批准每一次剪辑。")}</p>
      </header>
      {error && <p role="alert" className="error-box">{error}</p>}
      <section className="trend-grid">
        {items.map((item) => (
          <button key={item.id} className="trend-card" onClick={() => onOpen(item.id)}>
            <span className="eyebrow">{item.source}{item.sample ? " · sample" : ""} · {item.category}</span>
            <strong className="trend-score">{item.score}</strong>
            <span>{item.creator}</span>
            <small className="trend-meta"><span>{age(item.published_at)}</span><span>{item.signals.at(-1)?.views ?? 0}</span></small>
            <p>{item.caption}</p>
          </button>
        ))}
        {samples.map((sample) => (
          <article key={sample.key} className="trend-card">
            <span className="eyebrow">{sample.source} · sample · {sample.category}</span>
            <strong className="trend-score">{sample.score}</strong>
            <p>{sample.caption}</p>
            <small>{sample.note}</small>
            <button className="secondary" disabled={busy} onClick={() => void act("/samples/" + sample.key)}>{t("Use as reference", "用作参考")}</button>
          </article>
        ))}
      </section>
      <form className="trend-form director-card" onSubmit={(event) => void saveManual(event)}>
        <h2>{t("Add a public URL", "添加公开链接")}</h2>
        <p>{t("Paste a link and the numbers you can see. Lumen stores that text. It does not open the video.", "粘贴链接和你看到的数字。Lumen 只保存这些文字，不会打开视频。")}</p>
        <label>{t("URL", "链接")}<input required type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} /></label>
        <label>{t("Creator", "作者")}<input required value={form.creator} onChange={(e) => setForm({ ...form, creator: e.target.value })} /></label>
        <label>{t("Published", "发布时间")}<input required type="datetime-local" value={form.published_at} onChange={(e) => setForm({ ...form, published_at: e.target.value })} /></label>
        <label>{t("Duration, seconds", "时长（秒）")}<input required type="number" min={1} max={180} value={form.duration} onChange={(e) => setForm({ ...form, duration: e.target.value })} /></label>
        <label>{t("Caption", "文案")}<textarea value={form.caption} maxLength={2000} onChange={(e) => setForm({ ...form, caption: e.target.value })} /></label>
        <label>{t("Hashtags", "话题")}<input value={form.hashtags} onChange={(e) => setForm({ ...form, hashtags: e.target.value })} /></label>
        <label>{t("Audio or music", "声音或音乐")}<input value={form.audio} onChange={(e) => setForm({ ...form, audio: e.target.value })} /></label>
        <label>{t("Views", "观看")}<input type="number" min={0} value={form.views} onChange={(e) => setForm({ ...form, views: e.target.value })} /></label>
        <label>{t("Likes", "点赞")}<input type="number" min={0} value={form.likes} onChange={(e) => setForm({ ...form, likes: e.target.value })} /></label>
        <label>{t("Comments", "评论")}<input type="number" min={0} value={form.comments} onChange={(e) => setForm({ ...form, comments: e.target.value })} /></label>
        <label>{t("Shares", "分享")}<input type="number" min={0} value={form.shares} onChange={(e) => setForm({ ...form, shares: e.target.value })} /></label>
        <button className="primary" disabled={busy}>{t("Save trend", "保存趋势")}</button>
      </form>
    </div>
  );
}
