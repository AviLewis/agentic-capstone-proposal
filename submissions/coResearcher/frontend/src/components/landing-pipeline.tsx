"use client";

import { type CSSProperties } from "react";
import { usePipelineTicker, type PipelineStage } from "@/components/pipeline-ticker";

function hexToRgba(hex: string, alpha: number): string {
  const value = hex.replace("#", "");
  const r = parseInt(value.substring(0, 2), 16);
  const g = parseInt(value.substring(2, 4), 16);
  const b = parseInt(value.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function LandingPipeline() {
  const { stages, activeIndex, active, handleSelect } = usePipelineTicker();

  return (
    <div className="rail-card">
      <div className="chrome">
        <span className="dot" style={{ background: "#e8b04b" }} />
        <span className="dot" style={{ background: "#4ec97a" }} />
        <span className="dot" style={{ background: "#e88fb0" }} />
        <span className="font-mono chrome-label">pipeline · run live</span>
        <span
          className="font-mono chrome-progress"
          style={{ color: active.color }}
        >
          stage {activeIndex + 1} / {stages.length}
        </span>
      </div>

      <div className="rail">
        <div className="rail-line" />
        <div className="rail-packet-track">
          <span
            className="rail-packet"
            style={{
              background: active.color,
              boxShadow: `0 0 12px 2px ${active.color}`,
            }}
          />
        </div>
        <div className="rail-nodes">
          {stages.map((stage, i) => {
            const isActive = i === activeIndex;
            return (
              <button
                key={stage.id}
                type="button"
                onClick={() => handleSelect(i)}
                className="node"
              >
                <span
                  className="node-dot"
                  data-active={isActive || undefined}
                  style={
                    isActive
                      ? ({
                          background: stage.color,
                          "--glow": hexToRgba(stage.color, 0.75),
                        } as CSSProperties)
                      : undefined
                  }
                />
                <span
                  className="font-mono node-label"
                  style={{ color: isActive ? stage.color : "#6d7280" }}
                >
                  {stage.id}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <Caption stage={active} />

      <div className="font-mono gates">
        <span className="gate-item">
          <span className="gate-dot" />
          gate · pick questions
        </span>
        <span className="gate-item">
          <span className="gate-dot" />
          gate · approve plan
        </span>
      </div>

      <style jsx>{`
        .rail-card {
          position: relative;
          padding: 38px 34px 30px;
          background: linear-gradient(180deg, #1b1e24, #16181d);
          border: 1px solid #2a2d35;
          border-radius: 16px;
          box-shadow: 0 30px 80px rgba(0, 0, 0, 0.45);
        }
        .chrome {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 34px;
        }
        .dot {
          width: 11px;
          height: 11px;
          border-radius: 50%;
        }
        .chrome-label {
          margin-left: 12px;
          font-size: 11px;
          color: #6d7280;
        }
        .chrome-progress {
          margin-left: auto;
          font-size: 11px;
        }
        .rail {
          position: relative;
          height: 76px;
          margin: 0 6px;
        }
        .rail-line {
          position: absolute;
          top: 9px;
          left: 0;
          right: 0;
          height: 2px;
          background: #262a32;
        }
        .rail-packet-track {
          position: absolute;
          top: 6px;
          left: 0;
          right: 0;
          height: 8px;
          pointer-events: none;
        }
        .rail-packet {
          position: absolute;
          top: 0;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          transform: translateX(-50%);
          animation: packetTravel 4.4s linear infinite;
        }
        @keyframes packetTravel {
          0% {
            left: 0%;
            opacity: 0;
          }
          8% {
            opacity: 1;
          }
          92% {
            opacity: 1;
          }
          100% {
            left: 100%;
            opacity: 0;
          }
        }
        .rail-nodes {
          position: relative;
          display: flex;
          justify-content: space-between;
        }
        .node {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
          flex: none;
          cursor: pointer;
          background: none;
          border: none;
          padding: 0;
        }
        .node-dot {
          width: 15px;
          height: 15px;
          border-radius: 50%;
          background: #1d2026;
          border: 2px solid #2f333c;
          transition: all 0.35s;
        }
        .node-dot[data-active] {
          border: none;
          transform: scale(1.25);
          animation: railGlow 1.8s ease-in-out infinite alternate;
        }
        @keyframes railGlow {
          from {
            box-shadow:
              0 0 6px 0 var(--glow),
              0 0 0 0 var(--glow);
          }
          to {
            box-shadow:
              0 0 22px 4px var(--glow),
              0 0 0 4px rgba(255, 255, 255, 0.02);
          }
        }
        .node-label {
          font-size: 11.5px;
          transition: color 0.35s;
        }
        .gates {
          display: flex;
          justify-content: center;
          gap: 26px;
          margin-top: 22px;
          font-size: 10.5px;
          color: #6d7280;
        }
        .gate-item {
          display: inline-flex;
          align-items: center;
          gap: 7px;
        }
        .gate-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: #e8b04b;
        }
        @media (prefers-reduced-motion: reduce) {
          .rail-packet {
            animation: none;
            opacity: 0;
          }
          .node-dot[data-active] {
            animation: none;
            box-shadow: 0 0 16px 3px var(--glow);
          }
        }
      `}</style>
    </div>
  );
}

function Caption({ stage }: { stage: PipelineStage }) {
  return (
    <div
      className="caption"
      style={{ boxShadow: `inset 3px 0 0 ${stage.color}` }}
    >
      <span className="font-mono caption-tag" style={{ color: stage.color }}>
        {stage.tag}
      </span>
      <span className="caption-desc">{stage.description}</span>

      <style jsx>{`
        .caption {
          display: flex;
          align-items: flex-start;
          gap: 16px;
          margin-top: 30px;
          padding: 16px 20px;
          border-radius: 10px;
          background: #131519;
          border: 1px solid #262a32;
          min-height: 74px;
          transition: box-shadow 0.35s;
        }
        .caption-tag {
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.12em;
          flex: none;
          min-width: 118px;
        }
        .caption-desc {
          flex: 1;
          font-size: 14px;
          line-height: 1.5;
          color: #c6c4bf;
        }
      `}</style>
    </div>
  );
}
