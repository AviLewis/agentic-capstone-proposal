"use client";

import { useRouter } from "next/navigation";
import { BriefForm } from "@/components/brief-form";
import {
  PipelineChips,
  PipelineDescriptionBand,
  usePipelineTicker,
} from "@/components/pipeline-ticker";

export default function NewRun() {
  const router = useRouter();
  const ticker = usePipelineTicker();

  return (
    <div className="flex min-h-screen flex-col bg-[#16181d] text-[#e8e6e1]">
      <div className="flex items-center justify-between gap-4 border-b border-[#2a2d35] px-7 py-3.5">
        <span className="font-mono flex-none text-sm font-bold text-[#e8b04b]">
          co·researcher
        </span>
        <PipelineChips
          activeIndex={ticker.activeIndex}
          onSelect={ticker.handleSelect}
        />
      </div>
      <PipelineDescriptionBand stage={ticker.active} />

      <main className="flex flex-1 justify-center px-10 py-12">
        <div className="w-full max-w-[640px]">
          <p className="font-mono mb-2 text-[10.5px] tracking-[0.14em] text-[#e8b04b]">
            NEW RUN
          </p>
          <h1 className="mb-2.5 text-3xl font-bold tracking-tight text-white">
            What do you want to research?
          </h1>
          <p className="mb-7 max-w-[520px] text-sm leading-relaxed text-[#8b909c]">
            Describe your topic. The pipeline will ideate questions, review
            the literature, design methodology, draft plans, and rank them by
            feasibility — pausing twice for your input.
          </p>

          <BriefForm onCreated={(runId) => router.push(`/runs/${runId}`)} />
        </div>
      </main>
    </div>
  );
}
