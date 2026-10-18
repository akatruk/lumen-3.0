import { useEffect, useRef, useState } from "react";
import { Dubbing } from "./Dubbing";
import { FinalMusic } from "./FinalMusic";
import { MediaLibrary, type Asset, type MediaLibraryHandle } from "./MediaLibrary";
import { MusicEditor, type Music } from "./MusicEditor";
import { MusicPlan } from "./MusicPlan";
import type { Lang } from "./types";

/** Voice and music on the create-video page. Picture edits stay on Create video. */
export function ProjectAudio({ pid, lang }: { pid: string; lang: Lang }) {
  const library = useRef<MediaLibraryHandle>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [music, setMusic] = useState<Music | null>(null);
  const [revision, setRevision] = useState(1);

  async function loadAssets() {
    const response = await fetch(`/api/studio/projects/${pid}/assets`);
    if (response.ok) setAssets(await response.json());
  }

  useEffect(() => {
    let alive = true;
    async function load() {
      const response = await fetch(`/api/studio/projects/${pid}/manual`);
      if (!response.ok || !alive) return;
      const body = await response.json();
      setRevision(body.revision);
      if (body.edit?.music) setMusic(body.edit.music);
    }
    void load();
    void loadAssets();
    return () => {
      alive = false;
    };
  }, [pid]);

  return (
    <section className="project-audio" aria-label="Voice and music">
      <Dubbing embedded pid={pid} lang={lang} />
      <MusicPlan
        pid={pid}
        revision={revision}
        assets={assets.filter((asset) => asset.metadata.kind === "music")}
        lang={lang}
        suggestDisabled
        currentMusic={music}
        onUploadMusic={() => library.current?.openMusicUpload()}
        onAssetsChanged={loadAssets}
        onUse={(next) => setMusic(next)}
        onApplied={async () => {}}
      />
      <MediaLibrary ref={library} pid={pid} lang={lang} assets={assets} onChanged={loadAssets} />
      <MusicEditor
        pid={pid}
        lang={lang}
        assets={assets.filter((asset) => asset.metadata.kind === "music")}
        value={music}
        disabled={false}
        firstCut={null}
        onAnalyzed={loadAssets}
        onChange={setMusic}
        delivery={
          <FinalMusic
            pid={pid}
            lang={lang}
            music={music}
            disabled={!music}
            save={async () => revision}
          />
        }
      />
    </section>
  );
}
