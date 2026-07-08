import type { PlanContent } from "@/lib/types";

const SECTIONS: { key: keyof PlanContent; label: string }[] = [
  { key: "hypotheses", label: "HYPOTHESES" },
  { key: "methods", label: "METHODS" },
  { key: "data", label: "DATA" },
  { key: "risks", label: "RISKS" },
  { key: "resources", label: "RESOURCES" },
];

const sectionLabel =
  "font-mono mb-1 text-[9.5px] tracking-[0.12em] text-[#6d7280]";

function formatItem(item: unknown): string {
  if (item && typeof item === "object") {
    const { description, source } = item as {
      description?: string;
      source?: string | null;
    };
    const desc = (description ?? "").trim();
    const src = (source ?? "").trim();
    if (desc && src) return `${desc} — ${src}`;
    return desc || src || "";
  }
  return String(item);
}

export function PlanContentView({ content }: { content: PlanContent }) {
  return (
    <div className="flex flex-col gap-3.5 text-[12.5px] leading-relaxed">
      {content.objective && (
        <div>
          <p className={sectionLabel}>OBJECTIVE</p>
          <p className="m-0 text-[#c6c4bf]">{content.objective}</p>
        </div>
      )}
      {SECTIONS.map(({ key, label }) => {
        const items = content[key];
        if (!Array.isArray(items) || items.length === 0) return null;
        return (
          <div key={String(key)}>
            <p className={sectionLabel}>{label}</p>
            <ul className="m-0 list-disc space-y-1 pl-4 text-[#c6c4bf]">
              {items.map((item, i) => (
                <li key={i}>{formatItem(item)}</li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
