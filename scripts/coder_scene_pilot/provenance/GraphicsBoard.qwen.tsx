import { useCurrentFrame, interpolate, spring } from 'remotion';
import { useMemo } from 'react';

interface Event {
  id: string;
  text: string;
  role: 'category' | 'document';
  group: number;
  relation: 'alternative' | 'sequence' | null;
  appearFrame: number;
}

interface Props {
  frame: number;
  fps: number;
  width: number;
  height: number;
  activeGroup: number;
  activeId: string;
  events: Event[];
}

export const GraphicsBoard: React.FC<Props> = ({
  frame,
  width,
  height,
  activeGroup,
  activeId,
  events
}) => {
  const visibleEvents = useMemo(() => {
    return events
      .filter(event => 
        event.appearFrame <= frame && 
        event.group === activeGroup
      )
      .sort((a, b) => a.appearFrame - b.appearFrame);
  }, [frame, activeGroup, events]);

  return (
    <div style={{ width, height, position: 'relative' }}>
      {visibleEvents.map((event, index) => {
        const isVisible = event.appearFrame <= frame;
        const isCurrent = event.id === activeId;
        
        const opacity = interpolate(
          frame,
          [event.appearFrame - 10, event.appearFrame, event.appearFrame + 10],
          [0, 1, 1],
          { extrapolateRight: 'clamp' }
        );
        
        const scale = spring(isCurrent ? 1.05 : 1, { stiffness: 100, damping: 10 });
        
        const yPosition = interpolate(
          frame,
          [event.appearFrame - 10, event.appearFrame, event.appearFrame + 10],
          [20, 0, 0],
          { extrapolateRight: 'clamp' }
        );
        
        const cardWidth = event.role === 'category' ? 400 : 350;
        const cardHeight = event.role === 'category' ? 80 : 60;
        
        const left = (width - cardWidth) / 2;
        
        return (
          <div
            key={event.id}
            style={{
              position: 'absolute',
              left,
              top: 100 + index * 100 + yPosition,
              width: cardWidth,
              height: cardHeight,
              opacity,
              transform: `scale(${scale})`,
              zIndex: isCurrent ? 10 : 1,
              border: isCurrent ? '3px solid #0066cc' : event.role === 'category' ? '1px solid #0066cc' : '1px solid #ccc',
              backgroundColor: event.role === 'category' ? '#f0f8ff' : '#ffffff',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '10px',
              boxSizing: 'border-box',
              boxShadow: isCurrent ? '0 4px 12px rgba(0, 102, 204, 0.3)' : '0 2px 4px rgba(0, 0, 0, 0.1)',
              transition: 'all 0.3s ease'
            }}
          >
            <div style={{
              fontSize: event.role === 'category' ? '20px' : '16px',
              fontWeight: event.id === activeId ? 'bold' : 'normal',
              color: event.role === 'category' ? '#0066cc' : '#333',
              textAlign: 'center',
              wordWrap: 'break-word',
              lineHeight: '1.4'
            }}>
              {event.text}
            </div>
          </div>
        );
      })}
    </div>
  );
};
