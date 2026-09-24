import { useState } from "react";
import type { Lang } from "./types";
import { translate } from "./locale";
import { EFFECT_KEYS, LOOKS, readBoard, writeBoard, type EffectBoard, type EffectKey, type LookName } from "./look";

const NAMES: LookName[] = ["clean", "punch", "soft", "kinetic", "split"];

export function LookBoard({ lang }: { lang: Lang }) {
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const [board, setBoard] = useState<EffectBoard>(() => readBoard() || LOOKS.punch);
  const [saved, setSaved] = useState(() => readBoard() !== null);
  function commit(next: EffectBoard) {
    setBoard(next);
    writeBoard(next);
    setSaved(true);
  }
  function toggle(key: EffectKey) {
    commit({ ...board, effects: { ...board.effects, [key]: !board.effects[key] } });
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
  function preset(name: LookName) {
    if (name === "clean") return t("Clean", "干净");
    if (name === "punch") return t("Punch", "冲击");
    if (name === "soft") return t("Soft light", "柔光");
    if (name === "kinetic") return t("Kinetic", "动态");
    return t("Split story", "分屏故事");
  }
  const on = EFFECT_KEYS.filter((key) => board.effects[key]);
  const amount = board.amount;
  return (
    <div className="page look-page">
      <p className="page-kicker">
        <span className="live-dot" />
        {t("Visual effects", "视觉效果")}
      </p>
      <h1>{t("Visual effect plaque", "视觉效果面板")}</h1>
      <p className="look-lead">
        {t(
          "Turn an effect on or off and set its strength. The next style match follows this plaque. The finished film still uses only your footage.",
          "打开或关闭效果并设置强度。下一次风格匹配会遵循这个面板。成片仍然只用你的素材。",
        )}
      </p>
      <div className="look-layout">
        <section className="look-plaque" aria-label={t("Visual effect plaque", "视觉效果面板")}>
          <div className="look-plaque-band">
            <span>{preset(board.name)}</span>
            <strong>{Math.round(amount * 100)}%</strong>
          </div>
          <div className="look-presets" role="group" aria-label={t("Look presets", "效果预设")}>
            {NAMES.map((name) => (
              <button key={name} type="button" aria-pressed={board.name === name} onClick={() => commit(LOOKS[name])}>
                {preset(name)}
              </button>
            ))}
          </div>
          <label className="look-strength">
            {t("Strength", "强度")}
            <input
              type="range"
              min={0.4}
              max={1.6}
              step={0.1}
              value={amount}
              aria-valuetext={`${Math.round(amount * 100)}%`}
              onChange={(e) => commit({ ...board, amount: Number(e.target.value) })}
            />
          </label>
          <div className="look-switches" role="group" aria-label={t("Visual effects", "视觉效果")}>
            {EFFECT_KEYS.map((key) => (
              <button key={key} type="button" aria-pressed={board.effects[key]} onClick={() => toggle(key)}>
                {label(key)}
              </button>
            ))}
          </div>
          <p className="look-recipe">{on.length ? on.map(label).join(" · ") : t("Clean", "干净")}</p>
          {saved && <p role="status">{t("Saved on this device. Style match on the next project uses this plaque.", "已保存在此设备。下一个项目的风格匹配会使用这个面板。")}</p>}
        </section>
        <section className="look-stage" aria-label={t("Look stage", "效果预览")}>
          <h2>{t("Look stage", "效果预览")}</h2>
          <p>{t("Drag to compare the frame before and after this look.", "拖动滑块，比较应用这个效果前后的画面。")}</p>
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
  return (
    <div className="look-stage-wrap">
      <div className="look-phone">
        <div className="look-frame look-before">
          <Frame fx={{ blur: false, glow: false, shadow: false, color: false, speed: false, stabilize: false, kinetic: false, progress: false, split: false, screen: false }} amount={1} filter="" />
        </div>
        <div className="look-frame look-after" style={{ clipPath: `inset(0 ${100 - compare}% 0 0)` }}>
          <Frame fx={fx} amount={amount} filter={filter || "none"} />
        </div>
      </div>
      <label className="look-compare">
        {t("Compare", "对比")}
        <input type="range" min={0} max={100} value={compare} aria-label={t("Compare", "对比")} aria-valuetext={`${compare}%`} onChange={(e) => setCompare(Number(e.target.value))} />
        <span>
          {t("Before", "之前")} · {t("After", "之后")}
        </span>
      </label>
    </div>
  );
}

function Frame({
  fx,
  amount,
  filter,
}: {
  fx: EffectBoard["effects"];
  amount: number;
  filter: string;
}) {
  return (
    <div
      className={"look-picture" + (fx.screen ? " is-screen" : "") + (fx.split ? " is-split" : "")}
      style={{
        filter,
        boxShadow: fx.shadow ? `inset 0 0 ${Math.round(28 * amount)}px rgba(12,16,14,${Math.min(0.72, 0.28 * amount)})` : undefined,
      }}
    >
      <i className={"look-subject" + (fx.stabilize ? " is-steady" : " is-shaky")} style={fx.speed ? { transform: `scale(${(1 + 0.06 * amount).toFixed(2)})` } : undefined} />
      {fx.stabilize && <i className="look-steady" aria-hidden="true" />}
      {fx.glow && <i className="look-glow" style={{ opacity: Math.min(1, 0.45 * amount) }} />}
      {fx.kinetic && (
        <b className="look-kinetic" key={amount}>
          Aa
        </b>
      )}
      {fx.progress && <i className="look-progress" style={{ width: `${Math.round(46 * amount)}%` }} />}
    </div>
  );
}
