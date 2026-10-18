import { useEffect, useState } from "react";
import type { Lang } from "./types";

const ISSUES = [
  "irrelevant_media",
  "poor_animation",
  "visual_clutter",
  "caption_problem",
  "face_overlap",
  "weak_composition",
  "factual_error",
] as const;

const DIMENSIONS = [
  ["story", "Story", "История", "叙事"],
  ["media_relevance", "Media", "Медиа", "素材"],
  ["motion", "Motion", "Движение", "动效"],
  ["captions", "Captions", "Субтитры", "字幕"],
  ["composition", "Composition", "Композиция", "构图"],
  ["audio", "Audio", "Звук", "声音"],
  ["overall", "Overall", "Итог", "整体"],
] as const;

function text(lang: Lang, en: string, ru: string, zh: string) {
  if (lang === "zh") return zh;
  if (lang === "ru") return ru;
  return en;
}

export function QualityFeedback({
  lang,
  projectId,
  timestamp,
}: {
  lang: Lang;
  projectId: string;
  timestamp: number;
}) {
  const [generations, setGenerations] = useState<{ id: string }[]>([]);
  const [generationId, setGenerationId] = useState("");
  const [rating, setRating] = useState("");
  const [sceneTime, setSceneTime] = useState(timestamp.toFixed(1));
  const [dimensions, setDimensions] = useState<Record<string, string>>({});
  const [comments, setComments] = useState("");
  const [sceneId, setSceneId] = useState("");
  const [issue, setIssue] = useState<string>(ISSUES[0]);
  const [assets, setAssets] = useState("");
  const [treatment, setTreatment] = useState("");
  const [sceneNote, setSceneNote] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/projects/${projectId}/memory/generations`, { credentials: "same-origin" })
      .then((response) => (response.ok ? response.json() : { generations: [] }))
      .then((payload) => {
        if (cancelled) return;
        const rows = payload.generations || [];
        setGenerations(rows);
        setGenerationId((current) => current || rows[0]?.id || "");
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function post(path: string, body: unknown) {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(path, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw Error(payload.detail || payload.error || String(response.status));
      setMessage(text(lang, "Saved.", "Сохранено.", "已保存。"));
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const optional: Record<string, number> = {};
  for (const [key] of DIMENSIONS) {
    const raw = dimensions[key];
    if (raw) optional[key] = Number(raw);
  }

  return (
    <details className="director-card">
      <summary>{text(lang, "Quality feedback", "Оценка качества", "质量反馈")}</summary>
      <p className="muted">
        {text(
          lang,
          "Rates a finished generation. Nothing is stored until you submit.",
          "Оценка готовой генерации. Запись появляется только после отправки.",
          "评价已完成的生成。提交后才会保存。",
        )}
      </p>
      <label>
        {text(lang, "Generation", "Генерация", "生成")}
        <input
          value={generationId}
          onChange={(event) => setGenerationId(event.target.value)}
          list="quality-generations"
          maxLength={80}
        />
        <datalist id="quality-generations">
          {generations.map((row) => (
            <option key={row.id} value={row.id} />
          ))}
        </datalist>
      </label>
      <label>
        {text(lang, "Video score 1–10", "Оценка видео 1–10", "视频评分 1–10")}
        <input
          type="number"
          min={1}
          max={10}
          value={rating}
          onChange={(event) => setRating(event.target.value)}
        />
      </label>
      <div>
        {DIMENSIONS.map(([key, en, ru, zh]) => (
          <label key={key}>
            {text(lang, en, ru, zh)}
            <input
              type="number"
              min={1}
              max={10}
              placeholder="—"
              value={dimensions[key] || ""}
              onChange={(event) => setDimensions({ ...dimensions, [key]: event.target.value })}
            />
          </label>
        ))}
      </div>
      <label>
        {text(lang, "Comment", "Комментарий", "备注")}
        <textarea maxLength={4000} value={comments} onChange={(event) => setComments(event.target.value)} />
      </label>
      <button
        className="primary"
        type="button"
        disabled={busy || generationId.length < 4 || Number(rating) < 1 || Number(rating) > 10}
        onClick={() =>
          void post(`/api/projects/${projectId}/memory/reviews`, {
            generation_id: generationId,
            rating: Number(rating),
            comments,
            ...optional,
          })
        }
      >
        {text(lang, "Save video rating", "Сохранить оценку", "保存视频评分")}
      </button>
      <hr />
      <label>
        {text(lang, "Scene id", "Сцена", "场景")}
        <input value={sceneId} maxLength={80} onChange={(event) => setSceneId(event.target.value)} />
      </label>
      <label>
        {text(lang, "Time (seconds)", "Время (сек)", "时间（秒）")}
        <input type="number" min={0} step={0.1} value={sceneTime} onChange={(event) => setSceneTime(event.target.value)} />
        <button type="button" className="text-button" onClick={() => setSceneTime(timestamp.toFixed(1))}>
          {text(lang, "Use playhead", "Текущее время", "使用播放头")}
        </button>
      </label>
      <label>
        {text(lang, "Asset ids", "Ассеты", "素材编号")}
        <input value={assets} onChange={(event) => setAssets(event.target.value)} placeholder="asset_a, asset_b" />
      </label>
      <label>
        {text(lang, "Motion treatment", "Движение", "动效")}
        <input value={treatment} maxLength={200} onChange={(event) => setTreatment(event.target.value)} />
      </label>
      <label>
        {text(lang, "Issue", "Проблема", "问题")}
        <select value={issue} onChange={(event) => setIssue(event.target.value)}>
          {ISSUES.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
      </label>
      <label>
        {text(lang, "Scene comment", "Комментарий к сцене", "场景备注")}
        <textarea maxLength={4000} value={sceneNote} onChange={(event) => setSceneNote(event.target.value)} />
      </label>
      <button
        className="secondary"
        type="button"
        disabled={busy || generationId.length < 4 || !sceneId.trim()}
        onClick={() => {
          void post(`/api/projects/${projectId}/memory/scenes`, {
            generation_id: generationId,
            scene_id: sceneId.trim(),
            timestamp_seconds: Number(sceneTime),
            asset_ids: assets.split(/[,\s]+/).filter(Boolean).slice(0, 12),
            motion_treatment: treatment,
            issue_category: issue,
            comments: sceneNote,
          });
        }}
      >
        {text(lang, "Flag this scene", "Отметить сцену", "标记此场景")}
      </button>
      {message && <p>{message}</p>}
    </details>
  );
}
