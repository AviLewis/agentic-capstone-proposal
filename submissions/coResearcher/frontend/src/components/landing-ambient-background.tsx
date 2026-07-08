"use client";

export function LandingAmbientBackground({ glowTint }: { glowTint: string }) {
  return (
    <>
      <div className="grid-drift pointer-events-none absolute inset-0" />
      <div
        className="pointer-events-none absolute top-[-260px] left-1/2 h-[640px] w-[900px] -translate-x-1/2"
        style={{
          background: `radial-gradient(ellipse at center, ${glowTint} 0%, transparent 70%)`,
          filter: "blur(12px)",
        }}
      />
      <style jsx>{`
        .grid-drift {
          background-image:
            linear-gradient(#20242c 1px, transparent 1px),
            linear-gradient(90deg, #20242c 1px, transparent 1px);
          background-size: 56px 56px;
          opacity: 0.35;
          animation: gridDrift 40s linear infinite;
          mask-image: radial-gradient(
            ellipse 90% 60% at 50% 22%,
            #000 30%,
            transparent 78%
          );
          -webkit-mask-image: radial-gradient(
            ellipse 90% 60% at 50% 22%,
            #000 30%,
            transparent 78%
          );
        }
        @keyframes gridDrift {
          from {
            background-position: 0 0;
          }
          to {
            background-position: 0 -1600px;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .grid-drift {
            animation: none;
          }
        }
      `}</style>
    </>
  );
}
