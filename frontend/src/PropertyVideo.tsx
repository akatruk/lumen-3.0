import { useEffect, useState } from "react";
import type { Lang } from "./types";
import { workspaceText } from "./ProjectWorkspace";

const FACTS = ["price", "currency", "floor_area", "floor_area_unit", "bedrooms", "bathrooms", "floor", "tenure", "fees", "availability", "developer", "amenities"] as const;
const DESTINATIONS = ["douyin", "instagram_reels", "youtube_shorts", "tiktok", "xiaohongshu"] as const;
type FactKey = (typeof FACTS)[number];
type Fact = { key: FactKey; value: string; source: string; status: "supplied" | "verified" };
type Scene = { id: string; role: string; start: number; end: number; caption: string; fact_keys: string[]; location?: string };
type PropertyState = {
  brief?: Record<string, unknown>;
  plan?: { scenes: Scene[]; show_location: boolean; illustrative_in_picture: boolean; destinations: string[] };
  plan_revision?: number;
  approved_revision?: number | null;
  pending_render_id?: string;
  selected_render_id?: string;
  pending_cost?: { external_model_usd: number; note: string };
};

async function request(path: string, init?: RequestInit) {
  const response = await fetch("/api" + path, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Error(typeof data.detail === "string" ? data.detail : "request_failed");
  return data;
}

const json = (method: string, body: unknown) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function PropertyVideo({ pid, lang }: { pid: string; lang: Lang }) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  const [prop, setProp] = useState<PropertyState>({});
  const [audience, setAudience] = useState("");
  const [language, setLanguage] = useState<"en" | "zh" | "ru">("en");
  const [hook, setHook] = useState("");
  const [brand, setBrand] = useState("");
  const [cta, setCta] = useState("");
  const [contact, setContact] = useState("");
  const [location, setLocation] = useState("");
  const [showLocation, setShowLocation] = useState(false);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [highlights, setHighlights] = useState<FactKey[]>([]);
  const [destinations, setDestinations] = useState<string[]>(["youtube_shorts"]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const labels: Record<FactKey, string> = {
    price: w("Цена", "Price", "价格"),
    currency: w("Валюта", "Currency", "币种"),
    floor_area: w("Площадь", "Floor area", "建筑面积"),
    floor_area_unit: w("Единица площади", "Area unit", "面积单位"),
    bedrooms: w("Спальни", "Bedrooms", "卧室"),
    bathrooms: w("Санузлы", "Bathrooms", "卫生间"),
    floor: w("Этаж", "Floor", "楼层"),
    tenure: w("Право", "Tenure", "产权"),
    fees: w("Платежи", "Fees", "费用"),
    availability: w("Наличие", "Availability", "状态"),
    developer: w("Застройщик", "Developer", "开发商"),
    amenities: w("Инфраструктура", "Amenities", "配套"),
  };

  useEffect(() => {
    request("/studio/projects/" + pid + "/property").then((saved: PropertyState) => {
      setProp(saved);
      const brief = saved.brief as Record<string, unknown> | undefined;
      if (!brief) return;
      setAudience(String(brief.audience || ""));
      setLanguage((brief.language as "en" | "zh" | "ru") || "en");
      setHook(String(brief.hook || ""));
      setBrand(String(brief.brand || ""));
      const action = brief.cta as { text?: string; contact?: string } | undefined;
      setCta(action?.text || "");
      setContact(action?.contact || "");
      const where = brief.location as { label?: string; show?: boolean } | null;
      setLocation(where?.label || "");
      setShowLocation(Boolean(where?.show));
      setFacts((brief.facts as Fact[]) || []);
      setHighlights((brief.highlights as FactKey[]) || []);
      setDestinations((brief.destinations as string[]) || []);
      setScenes(saved.plan?.scenes || []);
    }).catch((reason: Error) => setError(reason.message));
  }, [pid]);

  const briefBody = () => ({
    audience,
    language,
    facts: facts.filter((fact) => fact.value.trim() && fact.source.trim()),
    highlights: highlights.filter((key) => facts.some((fact) => fact.key === key && fact.value.trim())),
    location: location.trim() ? { label: location.trim(), show: showLocation } : null,
    hook,
    brand,
    cta: { text: cta, contact },
    destinations,
  });

  const run = async (work: () => Promise<PropertyState>) => {
    setBusy(true);
    setError("");
    try {
      const next = await work();
      setProp(next);
      if (next.plan) setScenes(next.plan.scenes);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "request_failed");
    } finally {
      setBusy(false);
    }
  };

  const addFact = (key: FactKey) => {
    if (facts.some((fact) => fact.key === key)) return;
    setFacts([...facts, { key, value: "", source: "", status: "supplied" }]);
  };

  return (
    <section className="director-card">
      <h2>{w("Ролик об объекте", "Property video", "房产视频")}</h2>
      <p>
        {w(
          "В кадр попадают только ваши съёмки и факты, которые вы сами указали. Город не нужен. Референс задаёт приёмы и не попадает в ролик.",
          "The picture uses your footage and only the facts you enter. A city is not required. A reference video guides technique and is not copied into the cut.",
          "画面只使用你的素材和你填写的事实。不必填写城市。参考视频只提供手法，不会进入成片。",
        )}
      </p>
      {error && <p role="alert">{error}</p>}
      <label>
        {w("Аудитория", "Audience", "受众")}
        <input value={audience} onChange={(event) => setAudience(event.target.value)} />
      </label>
      <label>
        {w("Язык ролика", "Video language", "视频语言")}
        <select value={language} onChange={(event) => setLanguage(event.target.value as "en" | "zh" | "ru")}>
          <option value="en">English</option>
          <option value="zh">中文</option>
          <option value="ru">Русский</option>
        </select>
      </label>
      <label>
        {w("Первая фраза", "Opening line", "开场")}
        <input value={hook} onChange={(event) => setHook(event.target.value)} />
      </label>
      <label>
        {w("Бренд", "Brand", "品牌")}
        <input value={brand} onChange={(event) => setBrand(event.target.value)} />
      </label>
      <label>
        {w("Призыв", "Call to action", "行动号召")}
        <input value={cta} onChange={(event) => setCta(event.target.value)} />
      </label>
      <label>
        {w("Контакт", "Contact", "联系方式")}
        <input value={contact} onChange={(event) => setContact(event.target.value)} />
      </label>
      <label>
        {w("Локация, если её нужно показать", "Location, only if this video should show it", "地点，仅当本片需要显示时填写")}
        <input value={location} onChange={(event) => setLocation(event.target.value)} />
      </label>
      <label>
        <input type="checkbox" checked={showLocation} onChange={(event) => setShowLocation(event.target.checked)} />
        {w("Показать локацию в этом ролике", "Show the location in this video", "在本片中显示地点")}
      </label>
      <p>{w("Факты. Пустое поле не попадёт на экран.", "Facts. An empty field is left off the screen.", "事实。空白项不会出现在画面上。")}</p>
      {facts.map((fact, index) => (
        <div key={fact.key}>
          <strong>{labels[fact.key]}</strong>
          <input
            value={fact.value}
            aria-label={labels[fact.key]}
            onChange={(event) => setFacts(facts.map((item, itemIndex) => itemIndex === index ? { ...item, value: event.target.value } : item))}
          />
          <input
            value={fact.source}
            aria-label={w("Источник", "Source", "来源")}
            placeholder={w("Откуда факт", "Where this fact came from", "事实来源")}
            onChange={(event) => setFacts(facts.map((item, itemIndex) => itemIndex === index ? { ...item, source: event.target.value } : item))}
          />
          <select
            value={fact.status}
            aria-label={w("Статус", "Status", "状态")}
            onChange={(event) => setFacts(facts.map((item, itemIndex) => itemIndex === index ? { ...item, status: event.target.value as Fact["status"] } : item))}
          >
            <option value="supplied">{w("Сообщено", "Supplied", "已提供")}</option>
            <option value="verified">{w("Проверено", "Verified", "已核实")}</option>
          </select>
          <label>
            <input
              type="checkbox"
              checked={highlights.includes(fact.key)}
              onChange={(event) => setHighlights(event.target.checked ? [...highlights, fact.key] : highlights.filter((key) => key !== fact.key))}
            />
            {w("Показать в ролике", "Show in the video", "显示在视频中")}
          </label>
        </div>
      ))}
      <label>
        {w("Добавить факт", "Add a fact", "添加事实")}
        <select value="" onChange={(event) => event.target.value && addFact(event.target.value as FactKey)}>
          <option value="">{w("Выбрать", "Choose", "选择")}</option>
          {FACTS.filter((key) => !facts.some((fact) => fact.key === key)).map((key) => <option key={key} value={key}>{labels[key]}</option>)}
        </select>
      </label>
      <fieldset>
        <legend>{w("Куда готовим ролик", "Where this cut is aimed", "准备发布到")}</legend>
        {DESTINATIONS.map((destination) => (
          <label key={destination}>
            <input
              type="checkbox"
              checked={destinations.includes(destination)}
              onChange={(event) => setDestinations(event.target.checked ? [...destinations, destination] : destinations.filter((item) => item !== destination))}
            />
            {destination}
          </label>
        ))}
      </fieldset>
      <button type="button" className="secondary" disabled={busy} onClick={() => run(() => request("/studio/projects/" + pid + "/property", json("PUT", briefBody())))}>
        {w("Сохранить факты", "Save facts", "保存事实")}
      </button>
      <button type="button" className="secondary" disabled={busy} onClick={() => run(() => request("/studio/projects/" + pid + "/property/plan", json("POST", {})))}>
        {w("Собрать план", "Build the plan", "生成计划")}
      </button>
      {!!scenes.length && (
        <ol>
          {scenes.map((scene, index) => (
            <li key={scene.id}>
              <span>{scene.role} · {scene.start.toFixed(1)}–{scene.end.toFixed(1)}s</span>
              <input
                value={scene.caption}
                aria-label={scene.role}
                onChange={(event) => setScenes(scenes.map((item, itemIndex) => itemIndex === index ? { ...item, caption: event.target.value } : item))}
              />
            </li>
          ))}
        </ol>
      )}
      {!!scenes.length && (
        <button
          type="button"
          className="secondary"
          disabled={busy || !prop.plan_revision}
          onClick={() => run(() => request("/studio/projects/" + pid + "/property/plan", json("PUT", {
            revision: prop.plan_revision,
            scenes: scenes.map((scene) => ({ id: scene.id, caption: scene.caption })),
          })))}
        >
          {w("Сохранить план", "Save the plan", "保存计划")}
        </button>
      )}
      <button
        type="button"
        className="secondary"
        disabled={busy || !prop.plan_revision}
        onClick={() => run(() => request("/studio/projects/" + pid + "/property/approve", json("POST", { revision: prop.plan_revision })))}
      >
        {w("Утвердить план", "Approve the plan", "批准计划")}
      </button>
      <button
        type="button"
        disabled={busy || prop.approved_revision !== prop.plan_revision}
        onClick={() => run(async () => {
          const bytes = new Uint8Array(16);
          crypto.getRandomValues(bytes);
          const requestId = [...bytes].map((value) => value.toString(16).padStart(2, "0")).join("");
          await request("/studio/projects/" + pid + "/property/render", json("POST", { revision: prop.plan_revision, request_id: requestId }));
          for (let attempt = 0; attempt < 40; attempt += 1) {
            await new Promise((resolve) => setTimeout(resolve, 1500));
            const [next, current] = await Promise.all([
              request("/studio/projects/" + pid + "/property"),
              request("/projects/" + pid),
            ]);
            if (current.error) throw Error(current.error);
            if (next.pending_render_id && next.pending_revision === prop.plan_revision) return next;
          }
          throw Error("property_render_pending");
        })}
      >
        {w("Собрать ролик", "Render", "制作视频")}
      </button>
      {prop.pending_cost && <p>{w("Стоимость моделей в этом пакете", "Model cost in this package", "此包的模型费用")}: ${prop.pending_cost.external_model_usd}. {prop.pending_cost.note}</p>}
      {prop.pending_render_id && prop.pending_render_id !== prop.selected_render_id && (
        <div>
          <p>{w("Новая версия ждёт утверждения. Предыдущий файл не заменён.", "A new cut is waiting. The previous file is unchanged.", "新版本待确认。上一份文件未替换。")}</p>
          <video src={"/api/projects/" + pid + "/media/result?render=" + prop.pending_render_id} controls />
          <button type="button" disabled={busy} onClick={() => run(() => request("/studio/projects/" + pid + "/property/delivery", json("POST", { render_id: prop.pending_render_id })))}>
            {w("Утвердить эту версию", "Approve this cut", "批准此版本")}
          </button>
        </div>
      )}
      {prop.selected_render_id && (
        <div>
          <p>{w("Выбранная версия для просмотра и скачивания", "Selected cut for playback and download", "用于播放和下载的选定版本")}</p>
          <video src={"/api/projects/" + pid + "/media/result"} controls />
        </div>
      )}
      <p>
        {w(
          "Иллюстрации, если вы их приложите, в эту картинку не монтируются и не выдаются за объект. Публикация на площадки отсюда не запускается.",
          "Illustrations you attach are kept out of this picture and are not presented as the property. This step does not publish.",
          "你附加的示意图不会进入这条画面，也不会被当成真实房屋。此步骤不会发布。",
        )}
      </p>
    </section>
  );
}
