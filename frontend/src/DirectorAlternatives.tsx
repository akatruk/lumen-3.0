import {StatusBadge} from './TaskStatus';
import { useEffect, useState } from "react";
import type { Lang, Text } from "./types";
type Rec = {
  id: string;
  title: Text;
  improvement: Text;
  start: number;
  end: number;
  action: string;
};
type Proposal = {
  id: string;
  revision: number;
  target: string;
  instruction: string;
  status: string;
  proposal: null | {
    recommendation: Rec;
    transfer: { method: Text; fit: Text };
  };
};
export function DirectorAlternatives({
  pid,
  revision,
  recs,
  locked,
  disabled,
  lang,
  onApplied,
  onSave,
}: {
  pid: string;
  revision: number;
  recs: Rec[];
  locked: string[];
  disabled: boolean;
  lang: Lang;
  onApplied: () => Promise<void>;
  onSave?: () => Promise<void>;
}) {
  const t = (en: string, zh: string) => (lang === "zh" ? zh : en);
  const [items, setItems] = useState<Proposal[]>([]),
    [target, setTarget] = useState(""),
    [instruction, setInstruction] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const url = `/api/studio/projects/${pid}/alternatives`;
  async function load() {
    const r = await fetch(url);
    if (!r.ok)
      throw Error(t("Could not load alternatives.", "无法加载备选方案。"));
    setItems(await r.json());
  }
  useEffect(() => {
    let live = true;
    async function poll() {
      try {
        const r = await fetch(url);
        if (r.ok && live) setItems(await r.json());
      } catch {}
    }
    void poll();
    const timer = setInterval(poll, 4000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [url]);
  const pending = items.some((x) => x.status === "queued");
  async function act(path: string, data: unknown) {
    setBusy(true);
    setError("");
    try {
      const r = await fetch(url + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!r.ok)
        throw Error(
          t(
            "Could not apply this action. Save or refresh the plan, unlock the decision and wait for running jobs.",
            "操作失败。请保存或刷新计划，解锁决策，并等待当前任务完成。",
          ),
        );
      await load();
      if (path) await onApplied();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="director-card"
      aria-label={t("AI alternatives", "AI 备选方案")}
    >
      <h3>{t("Try another editing decision", "尝试其他剪辑方案")}</h3>
      <p>
        {t(
          "Describe what should improve. AI proposes one replacement; your current plan and finished videos stay unchanged until you apply and render it. This does not generate new footage. Reserves up to $0.50 within the project budget.",
          "描述需要改善的内容。AI 将提出一项替代建议；应用并制作前，当前计划和成片保持不变。此操作不会生成新画面，预留项目预算中的最多 $0.50。",
        )}
      </p>
      <label>
        {t("Decision", "决策")}
        <select
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          disabled={recs.length === 0}
        >
          <option value="">{t("Choose a decision", "选择决策")}</option>
          {recs.map((r) => (
            <option key={r.id} value={r.id}>
              {r.action === "normalize_audio"
                ? t("Normalize overall audio loudness", "统一整体音量")
                : r.title[lang]}
              {locked.includes(r.id) ? " 🔒" : ""}
            </option>
          ))}
        </select>
      </label>
      {recs.length===0 && <p role="status">{t("Decisions will appear after analysis finishes.","分析完成后将显示决策。")}</p>}
      {pending && <p role="status">{t("You can browse decisions while generation runs. Wait for it to finish before requesting another change.","生成期间可以查看决策。请等待完成后再提交新改动。")}</p>}
      {target && locked.includes(target) && <p role="status">{t("This decision is locked. Unlock and save it before requesting changes.","此决策已锁定。请求改动前请先解锁并保存。")}</p>}
      <label>
        {t("What should change?", "需要如何调整？")}
        <textarea
          value={instruction}
          maxLength={1200}
          onChange={(e) => setInstruction(e.target.value)}
        />
      </label>
      <button
        disabled={
          disabled ||
          busy ||
          pending ||
          !target ||
          locked.includes(target) ||
          instruction.trim().length < 3
        }
        onClick={() =>
          void act("", {
            revision,
            recommendation_id: target,
            instruction: instruction.trim(),
          })
        }
      >
        {t("Suggest alternative", "生成备选方案")}
      </button>
      {disabled && (
        <p>
          {t(
            "Save your plan changes before requesting or applying an alternative.",
            "请求或应用备选方案前，请先保存计划改动。",
          )}
        </p>
      )}
      {onSave && <button type="button" className="secondary" onClick={()=>void onSave()}>{t("Save plan to enable submission","保存计划以启用提交")}</button>}
      {error && <p role="alert">{error}</p>}
      {items.map((item) => (
        <article key={item.id}>
          <p>{item.instruction}</p>
          <StatusBadge status={item.status}>
            {
              (
                {
                  queued: t("Generating…", "生成中…"),
                  ready: t("Ready for review", "待审核"),
                  failed: t(
                    "Generation failed; original plan preserved.",
                    "生成失败，原计划已保留。",
                  ),
                  accepted: t(
                    "Applied to plan; review before rendering.",
                    "已应用到计划，制作前请审核。",
                  ),
                } as Record<string, string>
              )[item.status]
            }
          </StatusBadge>
          {item.proposal && (
            <>
              <h4>
                {item.proposal.recommendation.action === "normalize_audio"
                  ? t("Normalize overall audio loudness", "统一整体音量")
                  : item.proposal.recommendation.title[lang]}
              </h4>
              <p>
                {item.proposal.recommendation.action === "normalize_audio"
                  ? t(
                      "Adjusts overall mixed-track loudness only.",
                      "仅调整混合音轨的整体音量。",
                    )
                  : item.proposal.recommendation.improvement[lang]}
              </p>
              <p>
                {item.proposal.recommendation.start.toFixed(1)}–
                {item.proposal.recommendation.end.toFixed(1)}s ·{" "}
                {item.proposal.recommendation.action}
              </p>
              <p>{item.proposal.transfer.fit[lang]}</p>
            </>
          )}
          {item.status === "ready" &&
            (item.revision !== revision ? (
              <p>
                {t(
                  "The plan changed. Request a new alternative.",
                  "计划已更新，请重新生成方案。",
                )}
              </p>
            ) : (
              <button
                disabled={
                  disabled || busy || pending || locked.includes(item.target)
                }
                onClick={() =>
                  void act("/" + item.id + "/accept", { revision })
                }
              >
                {t("Replace this decision", "替换此决策")}
              </button>
            ))}
        </article>
      ))}
    </section>
  );
}
