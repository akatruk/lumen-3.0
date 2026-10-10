import { theme } from "../themes/tokens";
import type { KineticHookScene } from "../types/scene";
import { AutoFitText } from "../typography/AutoFitText";
import { DrawLine } from "../primitives/marks";
import { ScaleIn, SlideIn } from "../primitives/entrances";
import { tokenizeWords } from "../utils/words";
import { SafeArea, useSafeBox } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

export function KineticHook({ scene }: { scene: KineticHookScene }) {
  const box = useSafeBox();
  return (
    <SceneStage transition={scene.transition}>
      <SafeArea>
        {scene.variant === "scale_punch" ? (
          <ScalePunch text={scene.text} emphasis={scene.emphasis} width={box.width} height={box.height} />
        ) : scene.variant === "slide_stack" ? (
          <SlideStack text={scene.text} width={box.width} height={box.height} />
        ) : scene.variant === "rapid_reveal" ? (
          <div style={{ display: "flex", alignItems: "center", height: "100%", gap: theme.space.lg }}>
            <div style={{ width: 4, alignSelf: "stretch", background: theme.color.accent, borderRadius: theme.radius.pill }} />
            <AutoFitText
              text={scene.text}
              maxWidth={box.width - theme.space.lg - 4}
              maxHeight={box.height * 0.72}
              role={theme.type.hook}
              align="left"
              vertical="center"
              animate="mask"
              interval={3}
              wrapMode="word"
              emphasis={scene.emphasis}
            />
          </div>
        ) : (
          <AutoFitText
            text={scene.text}
            maxWidth={box.width}
            maxHeight={box.height * 0.7}
            role={theme.type.hook}
            align="center"
            vertical="center"
            animate="pop"
            interval={6}
            emphasis={scene.emphasis}
          />
        )}
      </SafeArea>
    </SceneStage>
  );
}

function ScalePunch({
  text,
  emphasis,
  width,
  height,
}: {
  text: string;
  emphasis?: string[];
  width: number;
  height: number;
}) {
  const cardWidth = Math.min(width, 920);
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <ScaleIn from={1.04} duration={20}>
        <div
          style={{
            width: cardWidth,
            background: theme.color.paper,
            color: theme.color.paperInk,
            borderRadius: theme.radius.lg,
            padding: theme.space.xl,
            boxShadow: theme.shadow.paper,
          }}
        >
          <AutoFitText
            text={text}
            maxWidth={cardWidth - theme.space.xl * 2}
            maxHeight={height * 0.42}
            role={theme.type.title}
            color={theme.color.paperInk}
            align="left"
            vertical="center"
            emphasis={emphasis}
            animate="none"
          />
          <div style={{ marginTop: theme.space.md }}>
            <DrawLine length={Math.min(180, cardWidth * 0.28)} thickness={3} delay={8} />
          </div>
        </div>
      </ScaleIn>
    </div>
  );
}

function SlideStack({ text, width, height }: { text: string; width: number; height: number }) {
  const words = tokenizeWords(text);
  const rowHeight = Math.min(220, (height - theme.space.md * Math.max(0, words.length - 1)) / Math.max(1, words.length));
  return (
    <div style={{ width, height, display: "flex", flexDirection: "column", justifyContent: "center", gap: theme.space.md }}>
      {words.map((word, index) => (
        <SlideIn key={`${word}-${index}`} direction="up" delay={index * 5} distance={20}>
          <div style={{ borderBottom: theme.border.hairline, paddingBottom: theme.space.sm }}>
            <AutoFitText
              text={word}
              maxWidth={width}
              maxHeight={rowHeight}
              role={theme.type.title}
              align="left"
              vertical="end"
              animate="none"
              wrapMode="word"
            />
          </div>
        </SlideIn>
      ))}
    </div>
  );
}
