import { translate, contentLanguage } from "./locale";
import type { Lang } from "./types";
import { clipLayers, clipSpan, formatSeconds, speedText, type TimedClip } from "./layerTiming";

type CardCopy = { en: string; zh: string };
type LayerClip = TimedClip & {
  shot_type?: string;
  card?: (TimedClip["card"] & { title?: CardCopy; primary?: CardCopy }) | null;
};

export function ClipLayerTracks({
  clip,
  lang,
  playhead,
}: {
  clip: LayerClip;
  lang: Lang;
  playhead?: number | null;
}) {
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const span = clipSpan(clip);
  const layers = clipLayers(clip);
  if (!span || !layers.length) return null;
  const roles: Record<string, string> = {
    presenter: t("Presenter", "讲解者"),
    close_up: t("Close-up", "特写"),
    medium: t("Medium shot", "中景"),
    broll: t("B-roll", "补充画面"),
    document: t("Document", "文档"),
    archive: t("Archival footage", "档案影像"),
    news: t("News clip", "新闻片段"),
  };
  const names: Record<string, string> = {
    shot: roles[clip.shot_type || "presenter"] || t("Presenter", "讲解者"),
    callout: t("Text", "文字"),
    card: t("Data cards", "数据卡片"),
    progress: t("Progress bar", "进度条"),
    blur: t("Blur", "模糊"),
    glow: t("Glow", "发光"),
    shadow: t("Shadow", "阴影"),
    speed: t("Speed", "速度"),
    cutout: t("Cutout", "抠像"),
    mask: t("Mask", "蒙版"),
    split: t("Split", "分屏"),
    reference: t("Reference copy", "参考画面"),
    art: t("Generated picture", "生成图片"),
    broll: t("B-roll", "补充画面"),
    join:
      {
        crossfade: t("Cross dissolve", "叠化"),
        zoom: t("Zoom transition", "缩放转场"),
        wipe: t("Wipe left", "向左擦除"),
        "wipe-up": t("Wipe up", "从下方出现"),
        "wipe-down": t("Wipe down", "从上方出现"),
        circle: t("Circle mask", "圆形遮罩"),
        fade: t("Fade through black", "淡入淡出至黑场"),
        diagtl: t("Wipe from the top left", "从左上角擦除"),
        diagtr: t("Wipe from the top right", "从右上角擦除"),
        diagbl: t("Wipe from the bottom left", "从左下角擦除"),
        diagbr: t("Wipe from the bottom right", "从右下角擦除"),
      }[clip.transition || ""] || t("Transition", "转场"),
  };
  const spoken = contentLanguage(lang);
  const head = playhead != null && playhead >= 0 && playhead <= span ? (playhead / span) * 100 : null;
  return (
    <section className="layer-tracks" aria-label={t("Layer timing", "图层时间")}>
      <p>{t("Entrance and exit already measured for this clip.", "此片段的入场和出场时间已经测得。")}</p>
      <div className="layer-scale">
        <span>0s</span>
        <span>{formatSeconds(span)}</span>
      </div>
      {layers.map((layer) => (
        <div className={`layer-row layer-row-${layer.id}`} key={layer.id}>
          <strong>{names[layer.id]}</strong>
          <div className="layer-lane">
            {layer.windows.map((window, index) => (
              <span
                key={index}
                style={{
                  left: `${(window.start / span) * 100}%`,
                  width: `${((window.end - window.start) / span) * 100}%`,
                }}
                title={`${formatSeconds(window.start)}–${formatSeconds(window.end)}`}
              >
                {layer.id === "callout"
                  ? clip.text
                  : layer.id === "card"
                    ? clip.card?.primary?.[spoken] || clip.card?.title?.[spoken] || ""
                    : layer.id === "speed"
                      ? speedText(clip)
                      : names[layer.id]}
              </span>
            ))}
            {head != null && <i className="layer-playhead" style={{ left: `${head}%` }} />}
          </div>
        </div>
      ))}
    </section>
  );
}
