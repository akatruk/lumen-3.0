import { translate, contentLanguage, translateRecord } from './locale';
import { useState, useRef, useEffect } from "react";
import {
  Search,
  Loader2,
  ArrowUpRight,
  ArrowRight,
  X,
  Heart,
  Clock3,
  Film,
} from "lucide-react";
import type { Lang } from "./types";
export type Hit = {
  id: string;
  aweme_id: string;
  title: string;
  author: string;
  duration: number;
  likes: number;
  cover: string | null;
  share_url: string;
};
type Results = { items: Hit[]; continuation: string | null; keyword: string };
const copy = {
  en: {
    title: "Find a video. Make it better.",
    intro:
      "Search Douyin, choose a video, and let Lumen find specific ways to improve it.",
    placeholder: "Search topics, products or ideas…",
    search: "Search Douyin",
    relevance: "Relevance",
    likes: "Most liked",
    latest: "Newest",
    any: "Any time",
    day: "Last 24 hours",
    week: "Last 7 days",
    months: "Last 180 days",
    empty: "No eligible videos found. Try another keyword or time range.",
    hint: "Video results up to 7 minutes · Chinese keywords work best for Douyin.",
    use: "Improve this video",
    original: "View on Douyin",
    more: "Load more",
    goal: "What should this video achieve?",
    goalHint:
      "For example: make the opening stronger and the product easier to understand.",
    language: "Output language",
    aspect: "Video format",
    originalSize: "Keep original",
    auto: "Automatically create an improved cut after analysis",
    generate: "Allow AI-generated inserts",
    budget: "AI budget for this project (USD)",
    cancel: "Cancel",
    importing: "Importing…",
    start: "Import & analyze",
    count: "videos",
    source: "Selected source",
    close: "Close",
  },
  zh: {
    title: "在抖音找视频，让内容更出彩。",
    intro: "搜索抖音，选择视频，让 Lumen 找出具体改进方向。",
    placeholder: "搜索主题、产品或创意…",
    search: "搜索抖音",
    relevance: "综合排序",
    likes: "最多点赞",
    latest: "最新发布",
    any: "不限时间",
    day: "近 24 小时",
    week: "近 7 天",
    months: "近 180 天",
    empty: "没有找到符合条件的视频，请更换关键词或时间范围。",
    hint: "仅展示 7 分钟以内的视频 · 建议使用中文关键词。",
    use: "改进这个视频",
    original: "在抖音查看",
    more: "加载更多",
    goal: "这支视频希望实现什么？",
    goalHint: "例如：增强开场吸引力，更清晰地展示产品。",
    language: "输出语言",
    aspect: "视频比例",
    originalSize: "保持原比例",
    auto: "分析后自动制作改进版",
    generate: "允许 AI 生成补充镜头",
    budget: "项目 AI 预算（美元）",
    cancel: "取消",
    importing: "正在导入…",
    start: "导入并分析",
    count: "个视频",
    source: "已选原视频",
    close: "关闭",
  },
};
const errors: Record<string, [string, string]> = {
  douyin_not_configured: [
    "Douyin search is not configured yet.",
    "抖音搜索暂未配置。",
  ],
  douyin_auth_failed: [
    "TikHub rejected its configured key.",
    "TikHub 密钥验证失败。",
  ],
  douyin_credits_required: [
    "TikHub needs account credits.",
    "TikHub 账户余额不足。",
  ],
  douyin_daily_limit: [
    "Daily search/import limit reached. Try again later.",
    "已达到每日搜索与导入上限，请稍后重试。",
  ],
  douyin_rate_limited: [
    "Too many requests. Please try again shortly.",
    "请求过于频繁，请稍后重试。",
  ],
  douyin_search_expired: [
    "These results expired. Please search again.",
    "搜索结果已过期，请重新搜索。",
  ],
  douyin_search_failed: [
    "Douyin search is temporarily unavailable. Please retry.",
    "抖音搜索暂时不可用，请重试。",
  ],
  too_many_jobs: [
    "You already have three videos processing.",
    "已有三个视频正在处理中。",
  ],
  storage_full: [
    "The workspace has insufficient storage.",
    "工作空间存储不足。",
  ],
  rate_limited: ["Please wait before trying again.", "请稍后再试。"],
  unauthorized: ["Please sign in again.", "请重新登录。"],
};
async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch("/api/douyin/" + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const d = await r.json();
  if (!r.ok)
    throw new Error(
      typeof d.detail === "string" ? d.detail : "douyin_search_failed",
    );
  return d;
}
const duration = (n: number) =>
  n
    ? `${Math.floor(n / 60)}:${String(Math.floor(n % 60)).padStart(2, "0")}`
    : "—";
export function DouyinSearch({
  lang,
  onImported,
  onSelect,
  selectedIds = [],
}: {
  lang: Lang;
  onImported: (id: string) => void;
  onSelect?: (hit: Hit) => void;
  selectedIds?: string[];
}) {
  const c = translateRecord(lang, copy.en, copy.zh);
  const [keyword, setKeyword] = useState(""),
    [sort, setSort] = useState("1"),
    [days, setDays] = useState("0"),
    [result, setResult] = useState<Results | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [selected, setSelected] = useState<Hit | null>(null);
  const submitted = useRef({ keyword: "", sort: "1", publish_time: 0 });
  const describe = (e: string) =>
    translate(lang, ...(errors[e] || [
      "Something went wrong. Please retry.",
      "操作失败，请重试。",
    ]) as [string, string]);
  async function search(more = false) {
    setBusy(true);
    setError("");
    if (!more) {
      submitted.current = {
        keyword: keyword.trim(),
        sort,
        publish_time: Number(days),
      };
      setResult(null);
    }
    try {
      const data = await post<Results>("search", {
        ...submitted.current,
        continuation: more ? result?.continuation || "" : "",
      });
      setResult((old) =>
        more && old
          ? {
              ...data,
              items: [
                ...old.items,
                ...data.items.filter(
                  (x) => !old.items.some((y) => y.aweme_id === x.aweme_id),
                ),
              ],
            }
          : data,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="douyin-search" aria-label={c.search}>
      <div className="douyin-heading">
        <span className="eyebrow">DOUYIN / 抖音</span>
        <h2>{onSelect ? (translate(lang, "Find your references", "寻找参考视频")) : c.title}</h2>
        <p>{onSelect ? (translate(lang, "Choose examples with useful pacing, structure and visual storytelling.", "选择值得借鉴的节奏、结构和画面表达。")) : c.intro}</p>
      </div>
      <form
        className="douyin-query"
        onSubmit={(e) => {
          e.preventDefault();
          void search();
        }}
      >
        <div className="douyin-query-input">
          <Search size={21} />
          <input
            aria-label={c.search}
            placeholder={c.placeholder}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            maxLength={120}
            required
            disabled={busy}
          />
        </div>
        <button className="primary" disabled={busy || !keyword.trim()}>
          {busy ? <Loader2 className="spin" size={18} /> : <Search size={18} />}{" "}
          {c.search}
        </button>
        <div className="douyin-filters">
          <select
            aria-label={translate(lang, "Sort results", "排序方式")}
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            disabled={busy}
          >
            <option value="1">{c.likes}</option>
            <option value="0">{c.relevance}</option>
            <option value="2">{c.latest}</option>
          </select>
          <select
            aria-label={translate(lang, "Publication date", "发布时间")}
            value={days}
            onChange={(e) => setDays(e.target.value)}
            disabled={busy}
          >
            <option value="0">{c.any}</option>
            <option value="1">{c.day}</option>
            <option value="7">{c.week}</option>
            <option value="180">{c.months}</option>
          </select>
          <span>{c.hint}</span>
        </div>
      </form>
      {error && (
        <p role="alert" className="error-box">
          {describe(error)}
        </p>
      )}
      {busy && !result && (
        <div className="douyin-loading" role="status">
          <Loader2 className="spin" size={24} />
          {c.search}…
        </div>
      )}
      {result && (
        <>
          <div className="douyin-result-count">
            “{result.keyword}” · {result.items.length} {c.count}
          </div>
          {!result.items.length && <p role="status">{c.empty}</p>}
          <div className="douyin-grid">
            {result.items.map((hit) => (
              <article className="douyin-card" key={hit.id}>
                <div className="douyin-cover">
                  <Film size={36} className="douyin-placeholder" />
                  {hit.cover && (
                    <img
                      src={hit.cover}
                      alt=""
                      loading="lazy"
                      referrerPolicy="no-referrer"
                      onError={(e) => {
                        e.currentTarget.style.display = "none";
                      }}
                    />
                  )}
                  <span>
                    <Clock3 size={12} />
                    {duration(hit.duration)}
                  </span>
                </div>
                <div className="douyin-card-body">
                  <h3 title={hit.title}>{hit.title}</h3>
                  <p>{hit.author || "Douyin"}</p>
                  <div className="douyin-card-meta">
                    <span>
                      <Heart size={14} />
                      {new Intl.NumberFormat(lang === "ru" ? "ru-RU" : lang === "zh" ? "zh-CN" : "en", {
                        notation: "compact",
                        maximumFractionDigits: 1,
                      }).format(hit.likes)}
                    </span>
                    <a
                      href={hit.share_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {c.original}
                      <ArrowUpRight size={14} />
                    </a>
                  </div>
                  <button
                    className="primary"
                    disabled={selectedIds.includes(hit.aweme_id)}
                    onClick={() =>
                      onSelect ? onSelect(hit) : setSelected(hit)
                    }
                  >
                    {onSelect
                      ? selectedIds.includes(hit.aweme_id)
                        ? translate(lang, "Added", "已添加")
                        : translate(lang, "Add reference", "添加为参考")
                      : c.use}
                    <ArrowRight size={16} />
                  </button>
                </div>
              </article>
            ))}
          </div>
          {result.continuation && (
            <button
              className="secondary douyin-more"
              disabled={busy}
              onClick={() => void search(true)}
            >
              {busy ? <Loader2 className="spin" size={18} /> : null}
              {c.more}
            </button>
          )}
        </>
      )}
      {selected && (
        <ImportDialog
          hit={selected}
          lang={lang}
          onClose={() => setSelected(null)}
          onImported={onImported}
          describe={describe}
        />
      )}
    </section>
  );
}
function ImportDialog({
  hit,
  lang,
  onClose,
  onImported,
  describe,
}: {
  hit: Hit;
  lang: Lang;
  onClose: () => void;
  onImported: (id: string) => void;
  describe: (s: string) => string;
}) {
  const c = translateRecord(lang, copy.en, copy.zh),
    ref = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      const p = await post<{ id: string }>("import", {
        result_id: hit.id,
        brief: f.get("brief"),
        language: f.get("language"),
        aspect: f.get("aspect"),
        budget: Number(f.get("budget")),
        auto_render: f.has("auto_render"),
        generative: f.has("generative"),
      });
      onImported(p.id);
      onClose();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={ref}
      className="douyin-import"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <div className="modal-header">
        <div>
          <span className="eyebrow">DOUYIN → LUMEN</span>
          <h2>{c.use}</h2>
        </div>
        <button
          className="icon"
          aria-label={c.close}
          onClick={onClose}
          disabled={busy}
        >
          <X size={20} />
        </button>
      </div>
      <form onSubmit={submit}>
        <div className="douyin-import-body">
          <small>{c.source}</small>
          <h3>{hit.title}</h3>
          <p>
            {hit.author} · {duration(hit.duration)}
          </p>
          {error && (
            <p role="alert" className="error-box">
              {describe(error)}
            </p>
          )}
          <label>
            {c.goal}
            <textarea
              name="brief"
              rows={3}
              maxLength={6000}
              placeholder={c.goalHint}
            />
          </label>
          <div className="douyin-import-options">
            <label>
              {c.language}
              <select name="language" defaultValue={contentLanguage(lang)}>
                <option value="en">English</option>
                <option value="zh">简体中文</option>
              </select>
            </label>
            <label>
              {c.aspect}
              <select name="aspect">
                <option value="original">{c.originalSize}</option>
                <option value="9:16">9:16</option>
                <option value="16:9">16:9</option>
                <option value="1:1">1:1</option>
              </select>
            </label>
            <label>
              {c.budget}
              <input
                type="number"
                name="budget"
                min={1}
                max={10}
                step="0.5"
                defaultValue={3}
              />
            </label>
          </div>
          <label className="douyin-check">
            <input type="checkbox" name="auto_render" defaultChecked />
            {c.auto}
          </label>
          <label className="douyin-check">
            <input type="checkbox" name="generative" />
            {c.generate}
          </label>
        </div>
        <div className="douyin-actions">
          <button
            type="button"
            className="text-button"
            onClick={onClose}
            disabled={busy}
          >
            {c.cancel}
          </button>
          <button className="primary" disabled={busy}>
            {busy ? (
              <>
                <Loader2 className="spin" size={17} />
                {c.importing}
              </>
            ) : (
              <>
                {c.start}
                <ArrowRight size={17} />
              </>
            )}
          </button>
        </div>
      </form>
    </dialog>
  );
}
