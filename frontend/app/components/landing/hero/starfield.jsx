"use client";

import { useMemo } from "react";
import { buildStarList } from "@/app/lib/stars";

function Starfield() {
  const stars = useMemo(() => buildStarList(), []);

  return (
    <div
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ transform: "translateZ(0)", transformStyle: "flat" }}
    >
      {stars.map((star) => (
        <div
          key={star.id}
          className="absolute rounded-full bg-emerald-300 animate-twinkle"
          style={{
            top: `${star.topPct}%`,
            left: `${star.leftPct}%`,
            width: `${star.sizePx}px`,
            height: `${star.sizePx}px`,
            transform: "translateZ(0px)",
            animationDelay: `${star.delayS}s`,
            animationDuration: `${star.durationS}s`,
            opacity: star.opacityStr,
            boxShadow: star.boxShadow,
          }}
        />
      ))}
    </div>
  );
}

export default Starfield;
