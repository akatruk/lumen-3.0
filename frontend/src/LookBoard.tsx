import { useEffect, useRef, useState } from "react";
import type { Lang } from "./types";
import { translate } from "./locale";
import {
  EFFECT_GROUPS,
  LOOKS,
  lookProjectId,
  parseBoard,
  readBoard,
  strengthAmount,
  strengthPercent,
  writeBoard,
  type EffectBoard,
  type EffectKey,
  type LookName,
} from "./look";

const NAMES: LookName[] = ["clean", "punch", "soft", "kinetic", "split"];

function cloneBoard(board: EffectBoard): EffectBoard {
  return { name: board.name, amount: board.amount, effects: { ...board.effects } };
}

function sameBoard(a: EffectBoard, b: EffectBoard) {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function LookBoard({ lang, onBack }: { lang: Lang; onBack: () => void }) {
  const projectId = lookProjectId();
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const [board, setBoard] = useState<EffectBoard>(() => cloneBoard(readBoard() || LOOKS.punch));
  const [savedBoard, setSavedBoard] = useState<EffectBoard>(() => cloneBoard(readBoard() || LOOKS.punch));
  const [persisted, setPersisted] = useState(() => (projectId ? false : readBoard() !== null));
  const [busy, setBusy] = useState(false);
  const [saveError, setSaveError] = useState("");
  const touched = useRef(false);
  const dirty = !sameBoard(board, savedBoard);
  const percent = strengthPercent(board.amount);

  useEffect(() => {
    if (!projectId) return;
    let live = true;
    fetch("/api/studio/projects/" + projectId, { credentials: "same-origin" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!live || !data) return;
        const saved = parseBoard(data.context?.effect_board ?? null);
        if (!saved) return;
        const next = cloneBoard(saved);
        setSavedBoard(next);
        setPersisted(true);
        if (!touched.current) setBoard(cloneBoard(saved));
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [projectId]);

  function toggle(key: EffectKey) {
    touched.current = true;
    setBoard({ ...board, effects: { ...board.effects, [key]: !board.effects[key] } });
  }
  function label(key: EffectKey) {
    if (key === "blur") return t("Blur", "模糊");
    if (key === "glow") return t("Glow", "发光");
    if (key === "shadow") return t("Shadow", "阴影");
    if (key === "color") return t("Color", "色彩");
    if (key === "speed") return t("Speed", "速度");
    if (key === "stabilize") return t("Stabilize", "防抖");
    if (key === "kinetic") return t("Moving type", "动态文字");
    if (key === "progress") return t("Progress", "进度");
    if (key === "split") return t("Split", "分屏");
    return t("Screen frame", "屏幕边框");
  }
  function hint(key: EffectKey) {
    if (key === "color") return t("Applies color, contrast, and exposure from the style match.", "使用风格匹配里的色彩、对比度和曝光。");
    if (key === "blur") return t("Softens the picture. Turn it off to keep the frame sharp.", "让画面变柔。关闭后画面保持清晰。");
    if (key === "glow") return t("Adds a soft bright halo.", "加上一层柔和的亮边。");
    if (key === "shadow") return t("Darkens the edges of the frame.", "压暗画面边缘。");
    if (key === "speed") return t("Speeds the clip up or slows it down.", "加快或放慢这段画面。");
    if (key === "stabilize") return t("Steadies a shaky shot.", "稳住抖动的镜头。");
    if (key === "kinetic") return t("Animates words when the clip already has text.", "片段已有文字时，让文字动起来。");
    if (key === "progress") return t("Draws a progress bar on the clip.", "在片段上画出进度条。");
    if (key === "split") return t("Shows two moments of your footage in one frame.", "在一个画面里放上你素材中的两个瞬间。");
    return t("Places the frame inside a screen border.", "把画面放进屏幕边框里。");
  }
  function preset(name: LookName) {
    if (name === "clean") return t("Clean", "干净");
    if (name === "punch") return t("Punch", "冲击");
    if (name === "soft") return t("Soft light", "柔光");
    if (name === "kinetic") return t("Kinetic", "动态");
    return t("Split story", "分屏故事");
  }
  function presetHint(name: LookName) {
    if (name === "clean") return t("No added effects. The frame stays close to your footage.", "不添加效果，画面接近你的素材。");
    if (name === "punch") return t("Stronger color, speed, a steady frame, moving type, and a progress bar.", "更强的色彩和速度、稳定画面、动态文字和进度条。");
    if (name === "soft") return t("Soft blur, glow, shadow, and color.", "柔和的模糊、发光、阴影和色彩。");
    if (name === "kinetic") return t("Color, moving type, a progress bar, and speed.", "色彩、动态文字、进度条和速度。");
    return t("A split frame, a screen border, color, and a progress bar.", "分屏、屏幕边框、色彩和进度条。");
  }
  function groupTitle(id: (typeof EFFECT_GROUPS)[number]["id"]) {
    if (id === "look") return t("Look", "效果");
    if (id === "light") return t("Light", "光线");
    if (id === "motion") return t("Motion", "运动");
    return t("Graphics", "图形");
  }
  async function save() {
    const next = cloneBoard(board);
    setSaveError("");
    if (!projectId) {
      writeBoard(next);
      setBoard(next);
      setSavedBoard(next);
      setPersisted(true);
      return;
    }
    setBusy(true);
    try {
      const response = await fetch("/api/studio/projects/" + projectId + "/effect-board", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      });
      if (!response.ok) throw new Error("save_failed");
      writeBoard(next);
      setBoard(next);
      setSavedBoard(cloneBoard(next));
      setPersisted(true);
    } catch {
      setSaveError(t("Could not save this recipe on the project. Try again.", "未能把这个配方保存到项目。请再试一次。"));
    } finally {
      setBusy(false);
    }
  }
  function cancel() {
    setBoard(cloneBoard(savedBoard));
  }

  return (
    <div className="page look-page">
      <div className="look-toolbar">
        <button type="button" className="text-button" onClick={onBack}>
          {t("Back", "返回")}
        </button>
        <div className="look-toolbar-actions">
          <button type="button" className="secondary" disabled={!dirty} onClick={cancel}>
            {t("Undo", "撤销")}
          </button>
          <button type="button" className="primary" disabled={busy || (!dirty && persisted)} onClick={() => void save()}>
            {t("Save", "保存")}
          </button>
        </div>
      </div>
      <h1>{t("Effect recipe", "效果配方")}</h1>
      <p className="look-lead">
        {projectId
          ? t(
              "This board is the effect recipe for the next picture render. The finished film still uses only your footage.",
              "这个面板是下一次画面渲染的效果配方。成片仍然只用你的素材。",
            )
          : t(
              "This board is the effect recipe for the next style match. The finished film still uses only your footage.",
              "这个面板是下一次风格匹配的效果配方。成片仍然只用你的素材。",
            )}
      </p>
      <div className="look-pro">
        <section className="look-panel" aria-label={t("Effect recipe", "效果配方")}>
          <label className="look-strength">
            <span>
              {t("Strength", "强度")}
              <strong>{percent}</strong>
            </span>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={percent}
              aria-valuetext={String(percent)}
              onChange={(e) => {
                touched.current = true;
                setBoard({ ...board, amount: strengthAmount(Number(e.target.value)) });
              }}
            />
          </label>
          {EFFECT_GROUPS.map((group) => (
            <section key={group.id} className="look-group" aria-labelledby={"look-group-" + group.id}>
              <h2 id={"look-group-" + group.id}>{groupTitle(group.id)}</h2>
              {group.id === "look" && (
                <label className="look-start">
                  <span>{t("Starting look", "起始效果")}</span>
                  <select
                    value={board.name}
                    onChange={(e) => {
                      touched.current = true;
                      setBoard(cloneBoard(LOOKS[e.target.value as LookName]));
                    }}
                  >
                    {NAMES.map((name) => (
                      <option key={name} value={name}>
                        {preset(name)}
                      </option>
                    ))}
                  </select>
                  <small>{presetHint(board.name)}</small>
                </label>
              )}
              {group.keys.map((key) => (
                <div key={key} className="look-row">
                  <button
                    type="button"
                    role="switch"
                    className="look-switch"
                    aria-checked={board.effects[key]}
                    aria-label={label(key)}
                    onClick={() => toggle(key)}
                  >
                    <span aria-hidden="true" />
                  </button>
                  <strong>{label(key)}</strong>
                  <p>{hint(key)}</p>
                </div>
              ))}
            </section>
          ))}
          <p role={saveError ? "alert" : "status"} className="look-status">
            {saveError
              ? saveError
              : dirty
                ? t("Unsaved changes", "尚未保存")
                : persisted
                  ? projectId
                    ? t("Saved on this project. The next picture render uses this recipe.", "已保存在此项目。下一次画面渲染会使用这个配方。")
                    : t("Saved on this device. Style match on the next project uses this plaque.", "已保存在此设备。下一个项目的风格匹配会使用这个面板。")
                  : projectId
                    ? t("Not saved yet. Save stores this recipe on the project.", "尚未保存。保存后，这个配方会写入项目。")
                    : t("Not saved yet. Save stores this recipe on this device.", "尚未保存。保存后，这个配方会留在此设备上。")}
          </p>
        </section>
        <section className="look-stage" aria-label={t("Before and after", "前后对比")}>
          <h2>{t("Before and after", "前后对比")}</h2>
          <p>{t("A still frame of your footage, before and after this look.", "你的素材的静止画面：这个效果之前和之后。")}</p>
          <Stage board={board} lang={lang} />
        </section>
      </div>
    </div>
  );
}

function Stage({ board, lang }: { board: EffectBoard; lang: Lang }) {
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const [compare, setCompare] = useState(68);
  const fx = board.effects;
  const amount = board.amount;
  const filter = [
    fx.blur ? `blur(${(1.1 * amount).toFixed(2)}px)` : "",
    fx.color ? `saturate(${(1 + 0.45 * amount).toFixed(2)}) contrast(${(1 + 0.12 * amount).toFixed(2)}) brightness(${(1 + 0.05 * amount).toFixed(2)})` : "",
  ]
    .filter(Boolean)
    .join(" ");
  const off = { blur: false, glow: false, shadow: false, color: false, speed: false, stabilize: false, kinetic: false, progress: false, split: false, screen: false };
  return (
    <div className="look-stage-wrap">
      <div className="look-pair">
        <figure>
          <figcaption>{t("Before", "之前")}</figcaption>
          <Frame fx={off} amount={1} filter="" plain />
        </figure>
        <figure>
          <figcaption>{t("After", "之后")}</figcaption>
          <Frame fx={fx} amount={amount} filter={filter || "none"} />
        </figure>
      </div>
      <label className="look-compare">
        {t("Compare", "对比")}
        <input type="range" min={0} max={100} step={1} value={compare} aria-label={t("Compare", "对比")} aria-valuetext={`${compare}%`} onChange={(e) => setCompare(Number(e.target.value))} />
        <span>
          {t("Before", "之前")} · {t("After", "之后")}
        </span>
      </label>
      <div className="look-wipe">
        <Frame fx={off} amount={1} filter="" plain />
        <div className="look-wipe-after" style={{ width: compare + "%" }}>
          <Frame fx={fx} amount={amount} filter={filter || "none"} />
        </div>
      </div>
    </div>
  );
}

function Frame({
  fx,
  amount,
  filter,
  plain,
}: {
  fx: EffectBoard["effects"];
  amount: number;
  filter: string;
  plain?: boolean;
}) {
  return (
    <div
      className={"look-still" + (fx.screen ? " is-screen" : "") + (fx.split ? " is-split" : "")}
      style={{
        filter,
        boxShadow: fx.shadow ? `inset 0 0 ${Math.round(28 * amount)}px rgba(12,16,14,${Math.min(0.72, 0.28 * amount)})` : undefined,
      }}
    >
      <i
        className="look-horizon"
        style={
          plain
            ? undefined
            : fx.speed
              ? { transform: `scale(${(1 + 0.06 * amount).toFixed(2)})` }
              : fx.stabilize
                ? undefined
                : { transform: "translate(8px, 0)" }
        }
      />
      {fx.glow && <i className="look-glow" style={{ opacity: Math.min(1, 0.45 * amount) }} />}
      {fx.kinetic && <b className="look-type">Aa</b>}
      {fx.progress && <i className="look-progress" style={{ width: `${Math.round(46 * amount)}%` }} />}
    </div>
  );
}
