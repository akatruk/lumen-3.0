import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

export function MenuSlide({
  className,
  label,
  marker,
  active,
  children,
}: {
  className: string;
  label: string;
  marker: string;
  active: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);
  const [frame, setFrame] = useState<{
    x: number;
    y: number;
    w: number;
    h: number;
  } | null>(null);
  const [motion, setMotion] = useState(false);

  useLayoutEffect(() => {
    const nav = ref.current;
    if (!nav) return;
    const place = () => {
      const item = nav.querySelector<HTMLElement>(marker);
      if (!item) {
        setFrame(null);
        return;
      }
      setFrame({
        x: item.offsetLeft,
        y: item.offsetTop,
        w: item.offsetWidth,
        h: item.offsetHeight,
      });
    };
    place();
    const id = requestAnimationFrame(() => setMotion(true));
    const observer = new ResizeObserver(place);
    observer.observe(nav);
    const item = nav.querySelector<HTMLElement>(marker);
    if (item) observer.observe(item);
    return () => {
      cancelAnimationFrame(id);
      observer.disconnect();
    };
  }, [marker, active]);

  return (
    <nav ref={ref} className={className} aria-label={label}>
      <span
        className={"menu-slide" + (motion ? " menu-slide-on" : "")}
        aria-hidden="true"
        style={
          frame
            ? {
                transform: `translate(${frame.x}px, ${frame.y}px)`,
                width: frame.w,
                height: frame.h,
              }
            : { opacity: 0 }
        }
      />
      {children}
    </nav>
  );
}
