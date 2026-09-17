import { translate, contentLanguage } from './locale';
import { useRef, useState } from "react";
import type { Lang } from "./types";
import content from "./tutorial-content.json";
export function TutorialVideos({
  lang,
  compact = false,
}: {
  lang: Lang;
  compact?: boolean;
}) {
  const [mode, setMode] = useState<"guide" | "walkthrough">(
    compact ? "guide" : "walkthrough",
  );
  const video = useRef<HTMLVideoElement>(null);
  const pendingSeek = useRef<{asset: string; time: number} | null>(null);
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const full = mode === "walkthrough";
  const duration = (seconds: number) => `${Math.floor(Math.round(seconds) / 60)}:${String(Math.round(seconds) % 60).padStart(2, "0")}`;
  const info = content[lang][mode];
  const asset = `/tutorial/lumen-${mode}-${contentLanguage(lang)}-v5`;
  return (
    <section
      className={
        "tutorial-video tutorial-v4 " + (compact ? "tutorial-compact" : "")
      }
      aria-label={t("Lumen video guide", "Lumen 视频使用指南")}
    >
      <div className="tutorial-copy">
        <span className="eyebrow">
          {t("LUMEN · VIDEO GUIDE", "LUMEN · 视频指南")}
        </span>
        <h2>
          {t("Meet Lumen. Then learn the workflow.", "认识 Lumen，掌握完整流程")}
        </h2>
        <p>
          {t(
            "Find references → add your footage → review the plan → render → export.",
            "寻找参考 → 上传自有素材 → 审核计划 → 制作 → 导出。",
          )}
        </p>
      </div>
      <div
        className="tutorial-tabs"
        role="group"
        aria-label={t("Choose a guide", "选择指南")}
      >
        <button aria-pressed={!full} onClick={() => setMode("guide")}>
          {t("Product presentation", "产品介绍")} · {duration(content[contentLanguage(lang)].guide.seconds)}
        </button>
        <button aria-pressed={full} onClick={() => setMode("walkthrough")}>
          {t("Full video guide", "完整操作指南")} · {duration(content[contentLanguage(lang)].walkthrough.seconds)}
        </button>
      </div>
      <video
        ref={video}
        key={asset}
        controls
        playsInline
        preload="none"
        onLoadedMetadata={() => {
          const pending = pendingSeek.current;
          if (pending?.asset === asset && video.current) {
            video.current.currentTime = pending.time;
            pendingSeek.current = null;
          }
        }}
        poster={asset + ".jpg"}
        aria-label={t(
          full ? "English step-by-step Lumen guide" : "English Lumen overview",
          full ? "Lumen 中文分步使用指南" : "Lumen 中文概览",
        )}
      >
        <source src={asset + ".mp4"} type="video/mp4" />
        <track
          kind="captions"
          src={asset + ".vtt"}
          srcLang={contentLanguage(lang)}
          label={contentLanguage(lang) === "zh" ? "简体中文" : "English"}
        />
      </video>
      <div className="tutorial-links">
        <span>
          {t("English narration and captions", "普通话配音与中文字幕")}
        </span>
        <a href={asset + ".mp4"} download>
          {t("Download video", "下载视频")}
        </a>
      </div>
      {full && (
        <>
          <div
            className="tutorial-chapters"
            role="group"
            aria-label={t("Guide chapters", "教学章节")}
          >
            {info.chapters.map((c, i) => (
              <button
                key={c.id}
                onClick={() => {
                  if (video.current) {
                    if (video.current.readyState >= 1) {
                      video.current.currentTime = c.start;
                    } else {
                      pendingSeek.current = {asset, time: c.start};
                    }
                    video.current.focus();
                    void video.current.play().catch(() => {});
                  }
                }}
              >
                {String(i + 1).padStart(2, "0")} · {c.title}
              </button>
            ))}
          </div>
          <details>
            <summary>{t("Read the instructions", "阅读文字说明")}</summary>
            <ol>
              {info.chapters.map((c) => (
                <li key={c.id}>
                  <strong>{c.title}</strong>
                  <p>{c.text}</p>
                </li>
              ))}
            </ol>
          </details>
        </>
      )}
    </section>
  );
}
