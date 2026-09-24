import { Trends } from "./Trends";
import {ProjectWorkspace, useWorkspace} from './ProjectWorkspace';
import { LanguageSelect } from './LanguageSelect';
import { translate, contentLanguage, readLanguage } from './locale';
import {StatusBadge} from './TaskStatus';
import { TutorialVideos } from "./TutorialVideos";
import { MenuSlide } from "./MenuSlide";
import React, {
  useState,
  useEffect,
  useRef,
  createContext,
  useContext,
} from "react";
import { createRoot } from "react-dom/client";
import {
  Plus,
  ArrowUpRight,
  ArrowRight,
  ChevronRight,
  ChevronDown,
  Upload,
  Film,
  ScanLine,
  Sparkles,
  Layers3,
  LayoutGrid,
  TrendingUp,
  Settings2,
  LogOut,
  Globe,
  Check,
  CheckCircle2,
  X,
  Play,
  Clock3,
  Search,
  SlidersHorizontal,
  Download,
  AlertCircle,
  Volume2,
  ShieldCheck,
  Loader2,
  Trash2,
  Menu,
  Eye,
  FileVideo,
  Scissors,
  Type,
  Image,
  Lightbulb,
  Target,
  ArrowLeft,
  LockKeyhole,
} from "lucide-react";
import { words, type Word } from "./i18n";
import type { Lang, Text, Project, Summary, Recommendation } from "./types";
import "./style.css";
import { DouyinSearch } from "./DouyinSearch";
import { StudioCreate, DirectorProject } from "./Studio";
import "./apple-design.css";
import "./workspace.css";
const Locale = createContext<{ lang: Lang; t: (key: string) => string }>({
  lang: "en",
  t: (k) => k,
});
const useL = () => useContext(Locale);
const fmt = (s: number) =>
  `${Math.floor(s / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(s % 60)
    .toString()
    .padStart(2, "0")}`;
function initialRoute() {
  const h = window.location.hash.slice(1);
  const trend = /^trend\/[a-f0-9]{32}$/.test(h) ? h.slice(6) : null;
  return {
    pid: /^project\/[a-f0-9]{32}$/.test(h) ? h.slice(8) : null,
    trend,
    page: trend ? "trends" : ["studio", "library", "settings", "guide", "trends"].includes(h) ? h : "studio",
  };
}
const active = (p: { status: string }) =>
  ["queued", "analyzing", "rendering"].includes(p.status);
async function api(path: string, init?: RequestInit) {
  const r = await fetch("/api" + path, { credentials: "same-origin", ...init });
  let d;
  try {
    d = await r.json();
  } catch {
    throw new Error("genericError");
  }
  if (!r.ok)
    throw new Error(typeof d.detail === "string" ? d.detail : "genericError");
  return d;
}
const json = (body: unknown) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
function Mark() {
  return (
    <span className="mark" aria-hidden>
      <i />
      <i />
      <i />
    </span>
  );
}
function Status({ status }: { status: string }) {
  const { t } = useL();
  return (
    <StatusBadge status={status}>{t("status_" + status)}</StatusBadge>
  );
}
function ErrorBox({ error }: { error: string }) {
  const { t } = useL();
  return (
    <div className="error-box" role="alert">
      <AlertCircle size={18} />
      <span>{t(error) === error ? t("genericError") : t(error)}</span>
    </div>
  );
}
function App() {
  const [lang, setLang] = useState<Lang>(
    readLanguage(localStorage.getItem("lumen_language")),
  );
  const t = (k: string) => (words[lang] as Record<string, string>)[k] || k;
  const [user, setUser] = useState<{ email: string } | null>(null),
    [loading, setLoading] = useState(true),
    [page, setPage] = useState(initialRoute().page),
    [trend, setTrend] = useState<string | null>(initialRoute().trend),
    [studioEpoch, setStudioEpoch] = useState(0),
    [items, setItems] = useState<Summary[]>([]),
    [pid, setPid] = useState<string | null>(initialRoute().pid),
    [project, setProject] = useState<Project | null>(null),
    [modal, setModal] = useState(false),
    [initialFile, setInitialFile] = useState<File | null>(null),
    [nav, setNav] = useState(false),
    [error, setError] = useState(""),
    [missingProject, setMissingProject] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const menuWasOpen = useRef(false);
  useEffect(() => {
    const change = () => {
      const r = initialRoute();
      setPage(r.page);
      setPid(r.pid);
      setTrend(r.trend);
    };
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  useEffect(() => {
    const next = pid ? "project/" + pid : trend ? "trend/" + trend : page;
    if (window.location.hash.slice(1) !== next) window.location.hash = next;
  }, [pid, page, trend]);
  useEffect(() => {
    api("/session")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem("lumen_language", lang);
  }, [lang]);
  useEffect(() => {
    if (nav) {
      menuWasOpen.current = true;
      sidebarRef.current?.querySelector<HTMLElement>("nav button")?.focus();
      const onKey = (event: KeyboardEvent) => {
        if (event.key === "Escape") setNav(false);
      };
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }
    if (menuWasOpen.current) {
      menuWasOpen.current = false;
      const button = menuButton.current;
      if (button && getComputedStyle(button).display !== "none") button.focus();
    }
  }, [nav]);
  const refresh = async () => {
    try {
      setItems(await api("/projects"));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    if (!user) return;
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, 7000);
    return () => clearInterval(timer);
  }, [user]);
  useEffect(() => {
    if (!pid) {
      setProject(null);
      setMissingProject(false);
      return;
    }
    let alive = true;
    let stopped = false;
    setMissingProject(false);
    const get = async () => {
      if (!alive || stopped) return;
      try {
        const p = await api("/projects/" + pid);
        if (!alive || stopped) return;
        setProject(p);
        setMissingProject(false);
      } catch (e) {
        if (!alive || stopped) return;
        if ((e as Error).message === "not_found") {
          stopped = true;
          window.clearInterval(timer);
          setProject(null);
          setMissingProject(true);
          setError("");
          return;
        }
        setError((e as Error).message);
      }
    };
    const timer = window.setInterval(() => void get(), 3500);
    void get();
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [pid]);
  const open = (id: string) => {
    setProject(null);
    setTrend(null);
    setPid(id);
    setNav(false);
  };
  const newProject = (file?: File) => {
    sessionStorage.removeItem("lumen-trend-handoff");
    setStudioEpoch((n) => n + 1);
    setPage("studio");
    setPid(null);
    setTrend(null);
    setNav(false);
  };
  const navigate = (p: string) => {
    setPage(p);
    setPid(null);
    setTrend(null);
    setNav(false);
  };
  const useTrend = (handoff: { concept_id: string; title: string; script: string; trend: string }) => {
    sessionStorage.setItem("lumen-trend-handoff", JSON.stringify(handoff));
    setStudioEpoch((n) => n + 1);
    setTrend(null);
    setPid(null);
    setPage("studio");
    setNav(false);
  };
  const logout = async () => {
    try {
      await api("/logout", { method: "POST" });
      setUser(null);
      setPid(null);
      setProject(null);
      setItems([]);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <Locale.Provider value={{ lang, t }}>
      {loading ? (
        <div className="loading">
          <Mark />
          <Loader2 className="spin" />
          <p>{t("loading")}</p>
        </div>
      ) : !user ? (
        <Auth onAuth={setUser} lang={lang} setLang={setLang} />
      ) : (
        <div className="app">
          {nav && (
            <button
              className="nav-scrim"
              aria-label={t("close")}
              onClick={() => setNav(false)}
            />
          )}
          <aside ref={sidebarRef} className={"sidebar " + (nav ? "mobile-open" : "")}>
            <button className="logo" onClick={() => navigate("studio")}>
              <Mark />
              <span>
                lumen<span className="logo-dot">.</span>
              </span>
            </button>
            <div className="workspace-name">
              <span className="workspace-avatar">L</span>
              <div>
                {translate(lang, "Lumen Workspace", "Lumen Workspace")}<small>{t("private")}</small>
              </div>
              <LockKeyhole size={13} />
            </div>
            <button
              className="primary sidebar-new"
              onClick={() => newProject()}
            >
              <Plus size={18} />
              {t("newProject")}
            </button>
            <div className="nav-label">{translate(lang, "WORKSPACE", "WORKSPACE")}</div>
            <MenuSlide
              className="sidebar-nav"
              label={translate(lang, "WORKSPACE", "WORKSPACE")}
              marker="button.active"
              active={pid ? "" : page}
            >
              {[
                ["studio", ScanLine],
                ["trends", TrendingUp],
                ["library", LayoutGrid],
                ["settings", Settings2],
                ["guide", Film],
              ].map(([key, Icon]) => {
                const K = Icon as typeof ScanLine;
                return (
                  <button
                    key={String(key)}
                    className={!pid && page === key ? "active" : ""}
                    onClick={() => navigate(String(key))}
                  >
                    <K size={19} />
                    {t(String(key))}
                    {key === "library" && (
                      <span className="nav-count">{items.length}</span>
                    )}
                  </button>
                );
              })}
            </MenuSlide>
            <div className="sidebar-note">
              <span className="tiny-orbit">
                <Sparkles size={20} />
              </span>
              <p>{t("draft")}</p>
              <small>{t("draftDesc")}</small>
            </div>
            <div className="sidebar-footer">
              <div className="account">
                <div className="avatar">{user.email[0].toUpperCase()}</div>
                <span title={user.email}>{user.email}</span>
                <button
                  aria-label={t("signOut")}
                  title={t("signOut")}
                  onClick={() => void logout()}
                >
                  <LogOut size={16} />
                </button>
              </div>
            </div>
          </aside>
          <main className="main">
            <header className="topbar">
              <div className="breadcrumb">
                <button
                  ref={menuButton}
                  className="icon mobile-menu"
                  aria-label={t("menu")}
                  aria-expanded={nav}
                  onClick={() => setNav(true)}
                >
                  <Menu size={21} />
                </button>
                <span>Lumen</span>
                <ChevronRight size={14} />
                <strong>
                  {pid
                    ? missingProject
                      ? t("projectMissing")
                      : project?.title || t("loading")
                    : t(page)}
                </strong>
              </div>
              <div className="topbar-right">
                <span className="edition">STUDIO / 01</span>
                <LanguageSelect lang={lang} onChange={setLang} />
              </div>
            </header>
            {error && (
              <div className="page-error">
                <ErrorBox error={error} />
                <button
                  className="icon"
                  onClick={() => setError("")}
                  aria-label={t("close")}
                >
                  <X size={16} />
                </button>
              </div>
            )}
            {pid ? (
              project ? (
                <ProjectWorkspace key={project.id} p={project} lang={lang} onBack={() => navigate("library")}>{project.studio ? (
                  <DirectorProject
                    key={project.id}
                    p={project}
                    lang={lang}
                    onBack={() => navigate("library")}
                    onRefresh={async () => {
                      setProject(await api("/projects/" + pid));
                      void refresh();
                    }}
                  />
                ) : (
                  <ProjectView
                    p={project}
                    onBack={() => navigate("library")}
                    onRefresh={async () => {
                      setProject(await api("/projects/" + pid));
                      void refresh();
                    }}
                    onDeleted={() => {
                      navigate("library");
                      void refresh();
                    }}
                  />
                )}</ProjectWorkspace>
              ) : missingProject ? (
                <div className="empty-centered">
                  <h2>{t("projectMissing")}</h2>
                  <p>{t("projectMissingDesc")}</p>
                  <button className="primary" onClick={() => navigate("library")}>
                    {t("backToProjects")}
                  </button>
                </div>
              ) : (
                <div className="loading">
                  <Loader2 className="spin" />
                  {t("loading")}
                </div>
              )
            ) : page === "studio" ? (
              <StudioCreate
                key={user.email + ":" + studioEpoch}
                lang={lang}
                userKey={user.email}
                onCreated={(id) => {
                  open(id);
                  void refresh();
                }}
              />
            ) : page === "trends" ? (
              <Trends
                lang={lang}
                trendId={trend}
                onOpen={(id) => {
                  setPid(null);
                  setTrend(id);
                  setPage("trends");
                }}
                onBack={() => navigate("trends")}
                onCreate={useTrend}
              />
            ) : page === "library" ? (
              <Library
                items={items}
                open={open}
                newProject={() => newProject()}
              />
            ) : page === "guide" ? (
              <div className="page tutorial-page"><TutorialVideos lang={lang}/></div>
            ) : (
              <Workspace />
            )}
          </main>
          {modal && (
            <UploadModal
              initial={initialFile}
              onClose={() => setModal(false)}
              onCreated={(p) => {
                setModal(false);
                setPid(p.id);
                setProject(p);
                void refresh();
              }}
            />
          )}
        </div>
      )}
    </Locale.Provider>
  );
}
function TutorialVideo({compact=false}:{compact?:boolean}) {const {lang}=useL();return <TutorialVideos lang={lang} compact={compact}/>;}

function Auth({
  onAuth,
  lang,
  setLang,
}: {
  onAuth: (u: { email: string }) => void;
  lang: Lang;
  setLang: (l: Lang) => void;
}) {
  const { t } = useL();
  const [account, setAccount] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="auth">
      <section className="auth-art">
        <div className="logo">
          <Mark />
          <span>lumen.</span>
        </div>
        <div className="auth-copy">
          <span className="eyebrow">{translate(lang, "VIDEO INTELLIGENCE STUDIO", "VIDEO INTELLIGENCE STUDIO")}</span>
          <h1>{t("welcome")}</h1>
          <p>{t("authDesc")}</p>
        </div>
        <div className="orbit-art">
          <div />
          <div />
          <div />
          <span>
            <Play fill="currentColor" size={44} />
          </span>
          <i className="orbit-dot" />
        </div>
        <footer>
          ENGLISH &nbsp; / &nbsp; 中文 &nbsp; / &nbsp; РУССКИЙ<span>{translate(lang, "01 — SEE THE POSSIBILITIES", "01 — SEE THE POSSIBILITIES")}</span>
        </footer>
      </section>
      <section className="auth-form">
        <LanguageSelect lang={lang} onChange={setLang} className="auth-lang" />
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const data = new FormData(e.currentTarget);
            setBusy(true);
            setError("");
            api(account ? "/register" : "/login", json({
              email: String(data.get("email") || ""),
              password: String(data.get("password") || ""),
              invite: String(data.get("invite") || ""),
            }))
              .then(onAuth)
              .catch((err) => setError((err as Error).message))
              .finally(() => setBusy(false));
          }}
        >
          <span className="eyebrow">{translate(lang, "LUMEN WORKSPACE", "LUMEN WORKSPACE")}</span>
          <h2>{account ? t("register") : t("signIn")}</h2>
          <p>{t("authDesc")}</p>
          <label>
            {t("email")}
            <input name="email" type="email" required autoComplete="username" />
          </label>
          <label>
            {t("password")}
            <input name="password" type="password" minLength={10} required autoComplete={account ? "new-password" : "current-password"} />
          </label>
          {account && (
            <label>
              {t("invite")}
              <input name="invite" required autoComplete="off" />
            </label>
          )}
          {error && (
            <p role="alert">{t(error) === error ? t("genericError") : t(error)}</p>
          )}
          <button className="primary" disabled={busy}>
            {busy ? <Loader2 className="spin" size={18} /> : t("continue")}
          </button>
        </form>
        <button type="button" className="auth-switch" onClick={() => { setAccount((value) => !value); setError(""); }}>
          {account ? t("haveAccount") : t("needAccount")}
        </button>
        <TutorialVideo compact />
        <small className="auth-foot">
          <ShieldCheck size={15} />
          {t("private")}
        </small>
      </section>
    </div>
  );
}
function Home({
  items,
  open,
  newProject,
  all,
}: {
  items: Summary[];
  open: (id: string) => void;
  newProject: (f?: File) => void;
  all: () => void;
}) {
  const { t, lang } = useL();
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  return (
    <div className="home page">
      <div className="page-kicker">
        <span className="live-dot" />
        {t("tagline")}
        <span className="kicker-line" />
      </div>
      <DouyinSearch lang={lang} onImported={open} />
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">{translate(lang, "LUMEN VIDEO STUDIO", "LUMEN VIDEO STUDIO")}</span>
          <h1>{t("hero")}</h1>
          <p>{t("intro")}</p>
          <div className="hero-caption">
            <span className="line" />
            <span>
              01 / {t("understand")} &nbsp; 02 / {t("improve")} &nbsp; 03 /{" "}
              {t("create")}
            </span>
          </div>
        </div>
        <div
          className={"upload-card " + (drag ? "drag" : "")}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            if (e.dataTransfer.files[0]) newProject(e.dataTransfer.files[0]);
          }}
        >
          <div className="frame-corners">
            <i />
            <i />
            <i />
            <i />
          </div>
          <div className="upload-symbol">
            <Film size={38} strokeWidth={1.25} />
            <span>
              <Plus size={13} />
            </span>
          </div>
          <h2>{t("drop")}</h2>
          <p>{t("formats")}</p>
          <button className="primary" onClick={() => input.current?.click()}>
            <Upload size={17} />
            {t("upload")}
            <ArrowUpRight size={17} />
          </button>
          <input
            ref={input}
            type="file"
            accept="video/mp4,video/quicktime,video/webm,.mov"
            hidden
            onChange={(e) => {
              if (e.target.files?.[0]) newProject(e.target.files[0]);
              e.target.value = "";
            }}
          />
          <span className="upload-private">
            <LockKeyhole size={12} />
            {t("private")}
          </span>
        </div>
      </section>
      <TutorialVideo />
      <section className="workflow">
        <div className="section-overline">{t("workflow")}</div>
        <div className="workflow-grid">
          {[
            [ScanLine, "understand", "understandDesc"],
            [SlidersHorizontal, "improve", "improveDesc"],
            [Sparkles, "create", "createDesc"],
          ].map(([Icon, title, desc], i) => {
            const I = Icon as typeof ScanLine;
            return (
              <article key={String(title)}>
                <div className="step-icon">
                  <I size={23} strokeWidth={1.4} />
                </div>
                <span className="step-number">0{i + 1}</span>
                <h3>{t(String(title))}</h3>
                <p>{t(String(desc))}</p>
              </article>
            );
          })}
        </div>
      </section>
      <section className="recent">
        <div className="section-title">
          <div>
            <span className="eyebrow">{t("latest")}</span>
            <h2>{t("recent")}</h2>
          </div>
          {items.length > 0 && (
            <button className="text-button" onClick={all}>
              {t("all")}
              <ArrowRight size={16} />
            </button>
          )}
        </div>
        {items.length ? (
          <div className="project-grid">
            {items.slice(0, 3).map((p) => (
              <ProjectCard key={p.id} p={p} onClick={() => open(p.id)} />
            ))}
          </div>
        ) : (
          <div className="empty-library">
            <Layers3 size={30} strokeWidth={1.2} />
            <div>
              <h3>{t("empty")}</h3>
              <p>{t("emptyDesc")}</p>
            </div>
            <button
              className="icon border"
              aria-label={t("newProject")}
              onClick={() => newProject()}
            >
              <Plus size={20} />
            </button>
          </div>
        )}
      </section>
      <footer className="page-footer">
        <span>{translate(lang, "LUMEN / VIDEO INTELLIGENCE", "LUMEN / VIDEO INTELLIGENCE")}</span>
        <span>ENGLISH · 中文 · РУССКИЙ</span>
      </footer>
    </div>
  );
}
function ProjectCard({ p, onClick }: { p: Summary; onClick: () => void }) {
  const { lang, t } = useL();
  const meta = p.metadata ? JSON.parse(p.metadata) : null;
  return (
    <button className="project-card" onClick={onClick}>
      <div className="project-cover">
        {!["queued"].includes(p.status) && (
          <img
            src={`/api/projects/${p.id}/media/poster`}
            alt=""
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
        )}
        <Film className="cover-fallback" size={30} />
        <span className="cover-play">
          <Play size={18} fill="currentColor" />
        </span>
        {meta && <span className="duration">{fmt(meta.duration)}</span>}
      </div>
      <div className="project-card-body">
        <Status status={p.status} />
        <h3>{p.title}</h3>
        <div className="project-card-meta">
          <span>
            {new Date(p.created * 1000).toLocaleDateString(
              lang === "ru" ? "ru-RU" : lang === "zh" ? "zh-CN" : "en-GB",
              { month: "short", day: "numeric" },
            )}{" "}
            · {p.language.toUpperCase()}
          </span>
          <ArrowUpRight size={17} />
        </div>
        {active(p) && (
          <div className="mini-progress" aria-label={t("processing")}>
            <i style={{ width: `${p.progress}%` }} />
          </div>
        )}
      </div>
    </button>
  );
}
function Library({
  items,
  open,
  newProject,
}: {
  items: Summary[];
  open: (id: string) => void;
  newProject: () => void;
}) {
  const { t, lang } = useL();
  const [q, setQ] = useState("");
  const filtered = items.filter((p) =>
    p.title.toLowerCase().includes(q.toLowerCase()),
  );
  return (
    <div className="page library">
      <div className="section-title">
        <div>
          <span className="eyebrow">{translate(lang, "LUMEN LIBRARY", "LUMEN LIBRARY")}</span>
          <h1>
            {t("library")}
            <span className="count">{items.length}</span>
          </h1>
        </div>
        <button className="primary" onClick={newProject}>
          <Plus size={18} />
          {t("newProject")}
        </button>
      </div>
      <div className="search">
        <Search size={18} />
        <input
          aria-label={t("search")}
          placeholder={t("search")}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {q && (
          <button
            className="icon"
            aria-label={t("clear")}
            onClick={() => setQ("")}
          >
            <X size={16} />
          </button>
        )}
      </div>
      {filtered.length ? (
        <div className="project-grid">
          {filtered.map((p) => (
            <ProjectCard key={p.id} p={p} onClick={() => open(p.id)} />
          ))}
        </div>
      ) : (
        <div className="empty-centered">
          <Layers3 size={36} />
          <h2>{t(q ? "noMatches" : "noProjects")}</h2>
          {!q && (
            <button className="primary" onClick={newProject}>
              {t("createFirst")}
              <Plus size={17} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
function UploadModal({
  initial,
  onClose,
  onCreated,
}: {
  initial: File | null;
  onClose: () => void;
  onCreated: (p: Project) => void;
}) {
  const { lang, t } = useL();
  const dialog = useRef<HTMLDialogElement>(null),
    fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState(initial),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [percent, setPercent] = useState(0);
  const xhr = useRef<XMLHttpRequest | null>(null);
  useEffect(() => {
    dialog.current?.showModal();
    return () => xhr.current?.abort();
  }, []);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file) return;
    setError("");
    if (file.size > 250 * 1024 * 1024) {
      setError("tooLarge");
      return;
    }
    setBusy(true);
    const f = new FormData(e.currentTarget);
    f.set("file", file);
    f.set("auto_render", f.has("auto_render") ? "true" : "false");
    f.set("generative", f.has("generative") ? "true" : "false");
    const req = new XMLHttpRequest();
    xhr.current = req;
    req.open("POST", "/api/projects");
    req.upload.onprogress = (e) => {
      if (e.lengthComputable)
        setPercent(Math.round((e.loaded / e.total) * 100));
    };
    req.onerror = () => {
      setError("uploadError");
      setBusy(false);
    };
    req.onload = () => {
      setBusy(false);
      try {
        const d = JSON.parse(req.responseText);
        if (req.status >= 200 && req.status < 300) onCreated(d);
        else setError(typeof d.detail === "string" ? d.detail : "genericError");
      } catch {
        setError("genericError");
      }
    };
    req.send(f);
  }
  return (
    <dialog
      ref={dialog}
      className="upload-modal"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <div className="modal-header">
        <div>
          <span className="eyebrow">{translate(lang, "A NEW STORY", "A NEW STORY")}</span>
          <h2>{t("newProject")}</h2>
        </div>
        <button
          className="icon"
          aria-label={t("close")}
          disabled={busy}
          onClick={onClose}
        >
          <X size={21} />
        </button>
      </div>
      <form onSubmit={submit}>
        <div className="modal-body">
          {error && <ErrorBox error={error} />}
          <button
            type="button"
            className={"file-picker " + (file ? "has-file" : "")}
            disabled={busy}
            onClick={() => fileInput.current?.click()}
          >
            <span className="file-icon">
              <FileVideo size={26} />
            </span>
            <span>
              <strong>{file?.name || t("choose")}</strong>
              <small>
                {file
                  ? `${(file.size / 1024 / 1024).toFixed(1)} MB · ${t("fileReady")}`
                  : t("formats")}
              </small>
            </span>
            <Upload size={18} />
          </button>
          <input
            ref={fileInput}
            hidden
            type="file"
            accept="video/mp4,video/quicktime,video/webm,.mov"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <label>
            {t("title")}
            <input
              name="title"
              maxLength={120}
              placeholder={
                file?.name.replace(/\.[^.]+$/, "") || t("newProject")
              }
              disabled={busy}
            />
          </label>
          <label>
            {t("brief")}
            <textarea
              name="brief"
              rows={3}
              maxLength={6000}
              placeholder={t("briefPlaceholder")}
              disabled={busy}
            />
            <small>{t("briefHint")}</small>
          </label>
          <div className="form-row">
            <label>
              {t("outputLang")}
              <select name="language" defaultValue={contentLanguage(lang)} disabled={busy}>
                <option value="en">English</option>
                <option value="zh">简体中文</option>
              </select>
            </label>
            <label>
              {t("format")}
              <select name="aspect" disabled={busy}>
                <option value="original">{t("original")}</option>
                <option value="9:16">{t("portrait")}</option>
                <option value="16:9">{t("landscape")}</option>
                <option value="1:1">{t("square")}</option>
              </select>
            </label>
          </div>
          <label className="toggle-row">
            <div>
              <strong>{t("auto")}</strong>
              <small>{t("autoDesc")}</small>
            </div>
            <input
              type="checkbox"
              name="auto_render"
              defaultChecked
              disabled={busy}
            />
          </label>
          <label className="toggle-row">
            <div>
              <strong>{t("gen")}</strong>
              <small>{t("genDesc")}</small>
            </div>
            <input type="checkbox" name="generative" disabled={busy} />
          </label>
          <label className="budget-row">
            <span>
              {t("budget")}
              <small>{t("budgetDesc")}</small>
            </span>
            <select name="budget" defaultValue="3" disabled={busy}>
              <option value="1">$1</option>
              <option value="3">$3</option>
              <option value="5">$5</option>
              <option value="10">$10</option>
            </select>
          </label>
          <div className="privacy-line">
            <ShieldCheck size={16} />
            {t("uploadPrivacy")}
          </div>
        </div>
        <div className="modal-footer">
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={onClose}
          >
            {t("cancel")}
          </button>
          <button className="primary" disabled={busy || !file}>
            {busy ? (
              <>
                <Loader2 size={17} className="spin" />
                {t("uploading")} {percent}%
              </>
            ) : (
              <>
                <ScanLine size={18} />
                {t("start")}
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
      </form>
    </dialog>
  );
}
const actionIcons: Record<string, typeof ScanLine> = {
  remove: Scissors,
  move_to_front: ArrowUpRight,
  captions: Type,
  normalize_audio: Volume2,
  generate_broll: Image,
};
function RecommendationCard({
  r,
  checked,
  disabled,
  toggle,
  seek,
}: {
  r: Recommendation;
  checked: boolean;
  disabled: boolean;
  toggle: () => void;
  seek: (s: number) => void;
}) {
  const { lang, t } = useL();
  const Icon = actionIcons[r.action] || Lightbulb;
  return (
    <article className={"recommendation " + (checked ? "chosen" : "")}>
      <div className="rec-top">
        <input
          aria-label={r.title[contentLanguage(lang)]}
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={toggle}
        />
        <span className={"rec-icon " + r.category}>
          <Icon size={18} />
        </span>
        <span className="rec-category">{t(r.category)}</span>
        <button className="timecode" onClick={() => seek(r.start)}>
          {fmt(r.start)}–{fmt(r.end)}
        </button>
      </div>
      <details>
        <summary>
          <h3>{r.title[contentLanguage(lang)]}</h3>
          <ChevronDown size={18} />
        </summary>
        <div className="rec-details">
          <span className="detail-label">{t("evidence")}</span>
          <p>{r.evidence[contentLanguage(lang)]}</p>
          <span className="detail-label">{t("improvement")}</span>
          <p>{r.improvement[contentLanguage(lang)]}</p>
          <button className="text-button" onClick={() => seek(r.start)}>
            <Play size={14} />
            {t("seek")}
          </button>
        </div>
      </details>
      <div className="rec-footer">
        <span>
          <i className={r.confidence >= 0.85 ? "high" : ""} />
          {Math.round(r.confidence * 100)}% {t("confidence")}
        </span>
        {r.auto_apply && r.confidence >= 0.85 && (
          <span className="recommended">
            <Sparkles size={11} />
            {t("safe")}
          </span>
        )}
        {disabled && r.action === "generate_broll" && (
          <small>{t("generationOff")}</small>
        )}
      </div>
    </article>
  );
}
function ProjectView({
  p,
  onBack,
  onRefresh,
  onDeleted,
}: {
  p: Project;
  onBack: () => void;
  onRefresh: () => Promise<void>;
  onDeleted: () => void;
}) {
  const { lang, t } = useL();
  const workspace=useWorkspace();
  const [tab, setTab] = useState("recommendations"),
    [videoMode, setVideoMode] = useState<"source" | "result">("source"),
    [time, setTime] = useState(0),
    [selected, setSelected] = useState<string[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [deleteOpen, setDeleteOpen] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const init = useRef("");
  const pendingSeek = useRef<number | null>(null);
  useEffect(() => {
    if (p.analysis && init.current !== p.id) {
      init.current = p.id;
      setSelected(
        p.analysis.recommendations
          .filter(
            (r) =>
              r.auto_apply &&
              r.confidence >= 0.85 &&
              (p.generative || r.action !== "generate_broll"),
          )
          .map((r) => r.id),
      );
    }
  }, [p]);
  const seek = (s: number) => {
    if(workspace){workspace.seekSource(s);return;}
    setTime(s);
    if (videoMode === "result") {
      pendingSeek.current = s;
      setVideoMode("source");
    } else if (video.current) {
      video.current.currentTime = s;
      video.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  };
  const toggle = (id: string) =>
    setSelected((xs) =>
      xs.includes(id) ? xs.filter((x) => x !== id) : [...xs, id],
    );
  const doRender = async () => {
    setBusy(true);
    setError("");
    try {
      await api(
        `/projects/${p.id}/render`,
        json({ recommendations: selected }),
      );
      setVideoMode("source");
      await onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const retry = async () => {
    setBusy(true);
    try {
      await api(`/projects/${p.id}/retry`, { method: "POST" });
      await onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const download = async () => {
    setBusy(true);
    try {
      const r = await fetch(`/api/projects/${p.id}/media/result`);
      if (!r.ok) throw Error();
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = p.title + "-lumen.mp4";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setError("downloadFailed");
    } finally {
      setBusy(false);
    }
  };
  const working = active(p);
  const a = p.analysis;
  const mediaReady = !!p.metadata?.preview_ready;
  const duration = p.metadata?.duration || 0;
  return (
    <div className="project-page">
      <div className="project-header ws-legacy-header">
        <div>
          <button className="text-button back" onClick={onBack}>
            <ArrowLeft size={14} />
            {t("library")}
          </button>
          <div className="project-heading">
            <h1>{p.title}</h1>
            <Status status={p.status} />
          </div>
          <p>
            {p.language === "en" ? "English" : "简体中文"} <span>·</span>{" "}
            {p.aspect === "original" ? t("original") : p.aspect} <span>·</span>{" "}
            {fmt(duration)}
          </p>
          {p.source?.platform === "douyin" && (
            <a
              className="source-attribution"
              href={p.source.share_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Douyin · {p.source.author || p.source.aweme_id}
              <ArrowUpRight size={14} />
            </a>
          )}
        </div>
        <div className="project-actions">
          <button
            className="icon border"
            disabled={working || busy}
            aria-label={t("deleteProject")}
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 size={17} />
          </button>
          {p.result && (
            <button
              className="primary"
              disabled={busy || working}
              onClick={() => void download()}
            >
              <Download size={17} />
              {t("export")}
            </button>
          )}
        </div>
      </div>
      {error && <ErrorBox error={error} />}
      <div className="studio-layout">
        <div className="preview-column">
          {!workspace && <div className="preview-panel">
            <div className="preview-toolbar">
              <div className="segment">
                <button
                  className={videoMode === "source" ? "active" : ""}
                  onClick={() => setVideoMode("source")}
                >
                  {t("originalVideo")}
                </button>
                <button
                  className={videoMode === "result" ? "active" : ""}
                  disabled={!p.result || working}
                  onClick={() => setVideoMode("result")}
                >
                  <Sparkles size={13} />
                  {t("newCut")}
                </button>
              </div>
              <span>
                {videoMode === "source"
                  ? p.metadata?.width
                  : p.result?.metadata.width}{" "}
                ×{" "}
                {videoMode === "source"
                  ? p.metadata?.height
                  : p.result?.metadata.height}
              </span>
            </div>
            <div className="video-stage">
              {mediaReady ? (
                <video
                  key={videoMode + p.id}
                  ref={video}
                  controls
                  playsInline
                  preload="metadata"
                  poster={`/api/projects/${p.id}/media/poster`}
                  src={`/api/projects/${p.id}/media/${videoMode}`}
                  onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
                  onLoadedMetadata={(e) => {
                    if (pendingSeek.current !== null) {
                      e.currentTarget.currentTime = pendingSeek.current;
                      pendingSeek.current = null;
                    }
                  }}
                />
              ) : (
                <div className="video-placeholder">
                  <ScanLine size={48} strokeWidth={1} />
                  <p>{t("stage_" + p.stage)}</p>
                </div>
              )}
            </div>
            <div className="timeline">
              <div className="timeline-label">
                <span>{t("sourceTimeline")}</span>
                <span>
                  {fmt(videoMode === "source" ? time : 0)} / {fmt(duration)}
                </span>
              </div>
              <div className="timeline-track">
                {a ? (
                  a.scenes.map((s, i) => (
                    <button
                      key={i}
                      title={`${fmt(s.start)} · ${s.title[contentLanguage(lang)]}`}
                      onClick={() => seek(s.start)}
                      style={{
                        left: `${(s.start / duration) * 100}%`,
                        width: `${((s.end - s.start) / duration) * 100}%`,
                      }}
                      className={"scene-block role-" + s.role}
                    >
                      <span>{String(i + 1).padStart(2, "0")}</span>
                    </button>
                  ))
                ) : (
                  <div className="timeline-empty" />
                )}
                {videoMode === "source" && (
                  <i
                    className="playhead"
                    style={{
                      left: `${Math.min((time / duration) * 100 || 0, 100)}%`,
                    }}
                  />
                )}
              </div>
              <div className="timeline-ticks">
                {[0, 0.25, 0.5, 0.75, 1].map((n) => (
                  <span key={n}>{fmt(duration * n)}</span>
                ))}
              </div>
            </div>
          </div>
          }
          {working && (
            <div className="processing-card">
              <span className="processing-icon">
                <Loader2 className="spin" size={22} />
              </span>
              <div>
                <strong>{t("stage_" + p.stage)}</strong>
                <p>
                  {t(
                    p.stage === "importing"
                      ? "douyinImportDesc"
                      : p.status === "queued"
                        ? "queueDesc"
                        : "pendingDesc",
                  )}
                </p>
                <div className="progress">
                  <i style={{ width: `${Math.max(4, p.progress)}%` }} />
                </div>
              </div>
              <span>{p.progress}%</span>
            </div>
          )}
          {p.error && (
            <div className="failure-card">
              <ErrorBox error={p.error} />
              {!a && (
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => void retry()}
                >
                  {t("retry")}
                </button>
              )}
            </div>
          )}
          {p.result && (
            <section className={"qa-card " + p.result.qa_status}>
              <div className="qa-title">
                {p.result.qa_status === "passed" ? (
                  <ShieldCheck size={22} />
                ) : (
                  <Eye size={22} />
                )}
                <div>
                  <span className="eyebrow">{t("quality")}</span>
                  <h3>
                    {t(
                      p.result.qa_status === "passed"
                        ? "qualityPass"
                        : p.result.qa_status === "unavailable"
                          ? "qualityUnavailable"
                          : "qualityFail",
                    )}
                  </h3>
                </div>
              </div>
              <p>{t("technicalPass")}</p>
              {p.result.qa?.issues.map((v, i) => (
                <p className="qa-issue" key={i}>
                  <AlertCircle size={15} />
                  {v[contentLanguage(lang)]}
                </p>
              ))}
              {p.result.qa?.observations.map((v, i) => (
                <p key={i}>
                  <Check size={14} />
                  {v[contentLanguage(lang)]}
                </p>
              ))}
              {!p.result.qa && <p>{t("reviewUnavailableDesc")}</p>}
              <small>{t("qualityNote")}</small>
              <div className="result-stats">
                <span>
                  {p.result.applied.length} {t("applied")}
                </span>
                <span>
                  {p.result.generated_clips} {t("generated")}
                </span>
                <span>{fmt(p.result.metadata.duration)}</span>
              </div>
            </section>
          )}
          <section className="brief-card">
            <div className="brief-title">
              <Target size={17} />
              <h3>{t("context")}</h3>
            </div>
            <p>{p.brief || t("noBrief")}</p>
            <div className="brief-meta">
              <span>
                {t("cost")}
                <strong>
                  ${p.cost.toFixed(3)} / ${p.budget.toFixed(2)}
                </strong>
              </span>
              <span>
                {t("audio")}
                <strong>{t(p.metadata?.has_audio ? "yes" : "no")}</strong>
              </span>
            </div>
            <small>{t("reserved")}</small>
          </section>
        </div>
        <div className="inspector">
          <div className="tabs" role="tablist">
            {["recommendations", "overview", "scenes", "transcript"].map(
              (k) => (
                <button
                  role="tab"
                  aria-selected={tab === k}
                  key={k}
                  className={tab === k ? "active" : ""}
                  onClick={() => setTab(k)}
                >
                  {t(k)}
                  {k === "recommendations" && a && (
                    <span>{a.recommendations.length}</span>
                  )}
                </button>
              ),
            )}
          </div>
          {!a ? (
            <div className="analysis-empty">
              <div className="analysis-orbit">
                <ScanLine size={34} />
              </div>
              <h2>
                {t(p.status === "failed" ? "stage_failed" : "analysisPending")}
              </h2>
              <p>
                {t(p.status === "failed" ? "processing_failed" : "pendingDesc")}
              </p>
              <div className="skeleton-line" />
              <div className="skeleton-line short" />
              <div className="skeleton-card" />
              <div className="skeleton-card" />
            </div>
          ) : tab === "recommendations" ? (
            <>
              <div className="inspector-intro">
                <span className="eyebrow">{translate(lang, "THE NEXT CUT", "THE NEXT CUT")}</span>
                <h2>{t("editPlan")}</h2>
                <p>{t("editDesc")}</p>
                <button
                  className="text-button reset-plan"
                  disabled={working}
                  onClick={() =>
                    setSelected(
                      a.recommendations
                        .filter(
                          (r) =>
                            r.auto_apply &&
                            r.confidence >= 0.85 &&
                            (p.generative || r.action !== "generate_broll"),
                        )
                        .map((r) => r.id),
                    )
                  }
                >
                  <Sparkles size={13} />
                  {t("resetSelection")}
                </button>
              </div>
              <div className="recommendations">
                {a.recommendations.length ? (
                  a.recommendations.map((r) => (
                    <RecommendationCard
                      key={r.id}
                      r={r}
                      checked={selected.includes(r.id)}
                      disabled={
                        working ||
                        (r.action === "generate_broll" && !p.generative)
                      }
                      toggle={() => toggle(r.id)}
                      seek={seek}
                    />
                  ))
                ) : (
                  <div className="empty-centered">
                    <CheckCircle2 size={28} />
                    <h3>{t("noRec")}</h3>
                    <p>{t("noRecDesc")}</p>
                  </div>
                )}
              </div>
              <div className="render-footer">
                <span>
                  <strong>{selected.length}</strong> {t("selected")}
                  <small>
                    {t("spendLabel")}: ${p.budget}
                  </small>
                </span>
                <button
                  className="primary"
                  disabled={working || busy}
                  onClick={() => void doRender()}
                >
                  {working || busy ? (
                    <Loader2 className="spin" size={17} />
                  ) : (
                    <Sparkles size={17} />
                  )}{" "}
                  {t(p.result ? "renderAgain" : "render")}
                </button>
              </div>
            </>
          ) : tab === "overview" ? (
            <div className="overview-content">
              <span className="eyebrow">{translate(lang, "THE BIG PICTURE", "THE BIG PICTURE")}</span>
              <h2>{t("overview")}</h2>
              <p className="analysis-summary">{a.summary[contentLanguage(lang)]}</p>
              <div className="insight green">
                <Lightbulb size={20} />
                <div>
                  <h3>{t("strongest")}</h3>
                  <p>{a.strongest_moment[contentLanguage(lang)]}</p>
                </div>
              </div>
              <h3 className="subheading">{t("editorial")}</h3>
              <p className="muted small">{t("subjective")}</p>
              <div className="scores">
                {a.scores.map((s) => (
                  <details key={s.category}>
                    <summary>
                      <span>{t(s.category)}</span>
                      <div className="score-bar">
                        <i style={{ width: s.value + "%" }} />
                      </div>
                      <strong>{s.value}</strong>
                      <ChevronDown size={14} />
                    </summary>
                    <p>{s.reason[contentLanguage(lang)]}</p>
                  </details>
                ))}
              </div>
              <div className="insight">
                <Target size={20} />
                <div>
                  <h3>{t("audience")}</h3>
                  <p>{a.audience[contentLanguage(lang)]}</p>
                </div>
              </div>
              {a.uncertainties.length > 0 && (
                <div className="uncertainties">
                  <h3>
                    <Eye size={17} />
                    {t("uncertainties")}
                  </h3>
                  {a.uncertainties.map((u, i) => (
                    <p key={i}>{u[contentLanguage(lang)]}</p>
                  ))}
                </div>
              )}
            </div>
          ) : tab === "scenes" ? (
            <div className="scene-list">
              <h2>{t("scenes")}</h2>
              {a.scenes.map((s, i) => (
                <button key={i} onClick={() => seek(s.start)}>
                  <span className="scene-num">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <span className="scene-meta">
                      {fmt(s.start)}—{fmt(s.end)} <b>{t(s.role)}</b>
                    </span>
                    <h3>{s.title[contentLanguage(lang)]}</h3>
                    <p>{s.observation[contentLanguage(lang)]}</p>
                  </div>
                  <Play size={16} />
                </button>
              ))}
            </div>
          ) : (
            <div className="transcript">
              <h2>{t("transcript")}</h2>
              {a.transcript.length ? (
                a.transcript.map((c, i) => (
                  <button
                    key={i}
                    className={
                      videoMode === "source" && time >= c.start && time < c.end
                        ? "speaking"
                        : ""
                    }
                    onClick={() => seek(c.start)}
                  >
                    <span>{fmt(c.start)}</span>
                    <div>
                      <p>{c[contentLanguage(lang)]}</p>
                      {c.original !== c[contentLanguage(lang)] && <small>{c.original}</small>}
                    </div>
                  </button>
                ))
              ) : (
                <div className="empty-centered">
                  <Volume2 size={28} />
                  <p>{t("noTranscript")}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {deleteOpen && (
        <Confirm
          onClose={() => setDeleteOpen(false)}
          onConfirm={async () => {
            try {
              await api(`/projects/${p.id}`, { method: "DELETE" });
              onDeleted();
            } catch (e) {
              setError((e as Error).message);
              setDeleteOpen(false);
            }
          }}
        />
      )}
    </div>
  );
}
function Confirm({
  onClose,
  onConfirm,
}: {
  onClose: () => void;
  onConfirm: () => Promise<void>;
}) {
  const { t, lang } = useL();
  const ref = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog ref={ref} className="confirm" onCancel={onClose}>
      <Trash2 size={24} />
      <h2>{t("deleteProject")}</h2>
      <p>{t("deleteConfirm")}</p>
      <div>
        <button className="secondary" disabled={busy} onClick={onClose}>
          {t("cancel")}
        </button>
        <button
          className="danger"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            void onConfirm();
          }}
        >
          {t("delete")}
        </button>
      </div>
    </dialog>
  );
}
function Workspace() {
  const { t, lang } = useL();
  const [caps, setCaps] = useState<{
    analysis: boolean;
    generation: boolean;
    analysis_model: string;
    generation_model: string;
  } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/capabilities")
      .then(setCaps)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <div className="page settings-page">
      <span className="eyebrow">{translate(lang, "LUMEN WORKSPACE", "LUMEN WORKSPACE")}</span>
      <h1>{t("settings")}</h1>
      <p className="muted">{t("workspaceDesc")}</p>
      {error && <ErrorBox error={error} />}
      <section className="settings-card">
        <h2>{t("connections")}</h2>
        <p>{t("connectionDesc")}</p>
        {[
          [ScanLine, "analysisProvider", caps?.analysis_model, caps?.analysis],
          [Sparkles, "genProvider", caps?.generation_model, caps?.generation],
          [Film, "renderProvider", "FFmpeg", true],
          [Layers3, "storage", t("localStorage"), true],
        ].map(([Icon, label, value, ok]) => {
          const I = Icon as typeof Film;
          return (
            <div className="connection" key={String(label)}>
              <span>
                <I size={20} />
              </span>
              <div>
                <strong>{t(String(label))}</strong>
                <small>{String(value || "…")}</small>
              </div>
              <span className={"connection-status " + (ok ? "ok" : "")}>
                {t(ok ? "available" : "notConfigured")}
              </span>
            </div>
          );
        })}
      </section>
      <div className="settings-grid">
        <section className="settings-card">
          <ShieldCheck size={24} />
          <h2>{t("privacyTitle")}</h2>
          <p>{t("privacyDesc")}</p>
        </section>
        <section className="settings-card">
          <Clock3 size={24} />
          <h2>{t("limits")}</h2>
          <p>{t("limitDesc")}</p>
        </section>
      </div>
      <section className="settings-card">
        <span className="eyebrow">RUNPOD</span>
        <h2>{t("runpod")}</h2>
        <p>{t("runpodDesc")}</p>
      </section>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
