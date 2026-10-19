// Types for the experimental graphics board. Clip rows live in fragment.ts.
export type GraphicsEvent = {
  id: string;
  text: string;
  role: 'category' | 'document';
  group: 1 | 2;
  relation: 'alternative' | 'sequence' | null;
  appearFrame: number;
};

export type GraphicsProps = {
  frame: number;
  fps: number;
  width: number;
  height: number;
  activeGroup: 1 | 2;
  activeId: string | null;
  events: GraphicsEvent[];
};
