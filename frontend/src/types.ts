export type Lang = "en" | "zh";
export type Text = { en: string; zh: string };
export type Recommendation = {
  id: string;
  start: number;
  end: number;
  title: Text;
  evidence: Text;
  improvement: Text;
  category: string;
  confidence: number;
  auto_apply: boolean;
  action: string;
  generation_prompt: string;
};
export type Metadata = {
  duration: number;
  width: number;
  height: number;
  has_audio: boolean;
  size: number;
  preview_ready?: boolean;
};
export type Analysis = {
  summary: Text;
  strongest_moment: Text;
  audience: Text;
  scores: { category: string; value: number; reason: Text }[];
  scenes: {
    start: number;
    end: number;
    title: Text;
    observation: Text;
    role: string;
  }[];
  transcript: {
    start: number;
    end: number;
    original: string;
    en: string;
    zh: string;
  }[];
  recommendations: Recommendation[];
  uncertainties: Text[];
};
export type Project = {
  studio?: boolean;
  source?: {
    platform: string;
    share_url: string;
    author: string;
    aweme_id: string;
  } | null;
  id: string;
  title: string;
  brief: string;
  language: Lang;
  aspect: string;
  auto_render: boolean;
  generative: boolean;
  budget: number;
  status: string;
  stage: string;
  progress: number;
  metadata: Metadata | null;
  analysis: Analysis | null;
  result: {
    render_id: string;
    plan_revision?: number;
    metadata: Metadata;
    timeline: number[][];
    applied: string[];
    generated_clips: number;
    qa_status: string;
    quality_score?:number;
    quality_comparison?:{previous_render_id:string;comparable:boolean;reason:string|null;previous_score?:number;current_score?:number;delta?:number;categories?:{category:string;previous:number;current:number;delta:number}[];regressions?:string[]}|null;
    quality_revision_id?:string;
    quality_revision_blocked?:string;
    qa: { passed: boolean; observations: Text[]; issues: Text[]; scores?:{category:string;value:number;reason:Text}[];revisions?:Text[] } | null;
  } | null;
  error: string | null;
  created: number;
  cost: number;
  events: { kind: string; detail: string; created: number }[];
};
export type Summary = Pick<
  Project,
  "id" | "title" | "status" | "stage" | "progress" | "language" | "created"
> & { metadata: string | null };
