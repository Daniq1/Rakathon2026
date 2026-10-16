// Text stránky dokumentu se zvýrazněnými citacemi faktů.
import { useEffect, useRef } from "react";
import type { Mark } from "../lib/highlight";
import { segment } from "../lib/highlight";

type Props = {
  text: string;
  marks: Mark[];
  activeFactId?: string | null;
  onMarkClick?: (mark: Mark) => void;
  markTitle?: (mark: Mark) => string;
};

export function DocumentText({ text, marks, activeFactId, onMarkClick, markTitle }: Props) {
  const activeRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const el = activeRef.current;
    if (!el) return;
    // Ve výřezu (.doc-excerpt) posunout jen výřez, ne celý panel
    const box = el.closest<HTMLElement>(".doc-excerpt");
    if (box) box.scrollTop = el.offsetTop - box.clientHeight / 2;
    else el.scrollIntoView({ block: "center" });
  }, [activeFactId, text]);

  let activeAssigned = false;
  return (
    <pre className="doc-text">
      {segment(text, marks).map((seg, i) => {
        if (seg.marks.length === 0) return <span key={i}>{seg.text}</span>;
        const active = seg.marks.some((m) => m.factId === activeFactId);
        const first = active && !activeAssigned;
        if (first) activeAssigned = true;
        const m = seg.marks.find((x) => x.factId === activeFactId) ?? seg.marks[0];
        return (
          <mark
            key={i}
            ref={first ? (el) => (activeRef.current = el) : undefined}
            className={active ? "quote active" : "quote"}
            title={markTitle ? seg.marks.map(markTitle).join("\n") : undefined}
            onClick={onMarkClick ? () => onMarkClick(m) : undefined}
          >
            {seg.text}
          </mark>
        );
      })}
    </pre>
  );
}
