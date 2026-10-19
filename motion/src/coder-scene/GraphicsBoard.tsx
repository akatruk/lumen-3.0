// Qwen composition, agent adaptation. Layout comes from sceneRules; the palette stays the model's.
import {interpolate, spring} from 'remotion';
import {useMemo} from 'react';
import type {GraphicsProps} from './graphicsContract';
import {CJK_FONT, boardMetrics, fitLabel, slotTop} from './sceneRules';

export const GraphicsBoard = ({
  frame,
  fps,
  width,
  height,
  activeGroup,
  activeId,
  events,
}: GraphicsProps) => {
  const groupEvents = useMemo(
    () => events.filter((event) => event.group === activeGroup).sort((a, b) => a.appearFrame - b.appearFrame),
    [events, activeGroup],
  );
  const metrics = boardMetrics(width, height, groupEvents.length);
  const protectedLabels = events.map((event) => event.text);

  return (
    <div style={{width, height, position: 'relative'}}>
      {groupEvents.map((event, index) => {
        if (event.appearFrame > frame) return null;
        const isCurrent = event.id === activeId;
        const role = event.role;
        const cardWidth = role === 'category' ? metrics.categoryWidth : metrics.documentWidth;
        const cardHeight = role === 'category' ? metrics.categoryHeight : metrics.documentHeight;
        const border = isCurrent ? 8 : role === 'category' ? 3 : 2;
        const preferred = role === 'category' ? metrics.categoryFont : metrics.documentFont;
        const fitted = fitLabel(event.text, cardWidth - 36 - border * 2 - 8, preferred, 28, protectedLabels);
        const opacity = interpolate(
          frame,
          [event.appearFrame - 8, event.appearFrame, event.appearFrame + 8],
          [0, 1, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );
        const emphasis = spring({
          frame: Math.max(0, frame - event.appearFrame),
          fps,
          config: {stiffness: 100, damping: 10},
        });
        const scale = isCurrent
          ? interpolate(emphasis, [0, 1], [1, metrics.activeScale], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
          : 1;
        const top = slotTop(metrics, index) + (metrics.slotHeight - cardHeight) / 2;

        return (
          <div
            key={event.id}
            style={{
              position: 'absolute',
              left: (width - cardWidth) / 2,
              top,
              width: cardWidth,
              height: cardHeight,
              opacity,
              transform: `scale(${scale})`,
              transformOrigin: 'center center',
              zIndex: isCurrent ? 10 : 1,
              border: `${border}px solid ${isCurrent || role === 'category' ? '#0066cc' : '#ccc'}`,
              backgroundColor: role === 'category' ? '#f0f8ff' : '#ffffff',
              borderRadius: 18,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '12px 18px',
              boxSizing: 'border-box',
              boxShadow: isCurrent ? '0 10px 28px rgba(0, 102, 204, 0.35)' : '0 4px 10px rgba(0, 0, 0, 0.12)',
            }}
          >
            <div
              style={{
                fontSize: fitted.fontSize,
                fontWeight: isCurrent || role === 'category' ? 700 : 500,
                color: role === 'category' ? '#0066cc' : '#333',
                textAlign: 'center',
                lineHeight: 1.15,
                whiteSpace: 'nowrap',
                fontFamily: CJK_FONT,
              }}
            >
              {fitted.lines.map((line, lineIndex) => (
                <div key={`${event.id}-${lineIndex}`}>{line}</div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};
