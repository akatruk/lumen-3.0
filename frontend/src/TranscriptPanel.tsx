import { useEffect, useState } from "react";
import { workspaceText } from "./ProjectWorkspace";
import type { Lang } from "./types";

type Segment = { id: string; start: number; end: number; text: string };

export function TranscriptPanel({
  pid,
  lang,
  onSeek,
}: {
  pid: string;
  lang: Lang;
  onSeek: (start: number, end?: number) => void;
}) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  const [rows, setRows] = useState<Segment[]>([]);
  const [status, setStatus] = useState("");
  const [version, setVersion] = useState<number | null>(null);
  const [language, setLanguage] = useState("");
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");

  async function load() {
    const response = await fetch("/api/studio/projects/" + pid + "/source-transcript", { credentials: "same-origin" });
    if (!response.ok) return;
    const body = await response.json();
    setStatus(body.status || "missing");
    setVersion(body.version ?? null);
    setLanguage(body.sourceLanguage || "");
    setRows(body.segments || []);
  }

  useEffect(() => {
    void load();
  }, [pid]);

  async function save(row: Segment) {
    const text = (draft[row.id] ?? row.text).trim();
    const response = await fetch("/api/studio/projects/" + pid + "/source-transcript", {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ segment_id: row.id, text }),
    });
    if (!response.ok) {
      setNote(w("Правка не сохранилась.", "The correction was not saved.", "修改没有保存。"));
      return;
    }
    setNote(w("План для следующего ролика сброшен. Готовый файл не менялся.", "The next plan was cleared. The finished file was not changed.", "下次计划已失效。已完成的文件没有改动。"));
    await load();
  }

  async function retry() {
    const response = await fetch("/api/studio/projects/" + pid + "/transcription/retry", {
      method: "POST",
      credentials: "same-origin",
    });
    const body = await response.json().catch(() => ({}));
    setNote(body.kept
      ? w("Проверенная расшифровка сохранена.", "The verified transcript was kept.", "已校验的字幕稿已保留。")
      : w("Расшифровка поставлена в очередь.", "Transcription was queued.", "转写已排队。"));
    await load();
  }

  return (
    <section className="source-transcript" aria-label={w("Расшифровка", "Transcript", "字幕稿")}>
      <header>
        <strong>{w("Расшифровка", "Transcript", "字幕稿")}</strong>
        <span>{language || w("язык не определён", "language not set", "语言未确定")} · {status}{version ? ` · v${version}` : ""}</span>
      </header>
      {status === "missing" || status === "transcription_failed" ? (
        <p>{w("Нет проверенной расшифровки.", "No verified transcript.", "没有经过校验的字幕稿。")}</p>
      ) : null}
      <ol>
        {rows.map((row) => (
          <li key={row.id}>
            <button type="button" onClick={() => onSeek(row.start, row.end)}>
              {row.start.toFixed(1)}–{row.end.toFixed(1)}
            </button>
            <input
              value={draft[row.id] ?? row.text}
              onChange={(event) => setDraft((current) => ({ ...current, [row.id]: event.target.value }))}
            />
            <button type="button" onClick={() => void save(row)}>{w("Сохранить", "Save", "保存")}</button>
          </li>
        ))}
      </ol>
      <button type="button" onClick={() => void retry()}>{w("Повторить расшифровку", "Retry transcription", "重试转写")}</button>
      {note ? <p role="status">{note}</p> : null}
    </section>
  );
}
