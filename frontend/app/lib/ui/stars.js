const STYLE_DECIMALS = 4;

const seeded = (seed) => {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
};

const styleNum = (n) => {
  return Number(n).toFixed(STYLE_DECIMALS);
};

const buildStarList = () => {
  const createCluster = (centerX, centerY, count, spread, baseSeed) => {
    return Array.from({ length: count }, (_, i) => {
      const s = baseSeed + i * 7;
      const angle = seeded(s) * Math.PI * 2;
      const distance = seeded(s + 1) * spread;
      const x = centerX + Math.cos(angle) * distance;
      const y = centerY + Math.sin(angle) * distance;
      const depth = seeded(s + 2) * 200 - 50;
      const depthFactor = 1 + depth / 200;
      return {
        top: `${Math.max(0, Math.min(100, y))}%`,
        left: `${Math.max(0, Math.min(100, x))}%`,
        size: (seeded(s + 3) * 3 + 1) * depthFactor,
        depth,
        delay: seeded(s + 4) * 5,
        duration: seeded(s + 5) * 3 + 2,
        opacity: Math.max(
          0.14,
          Math.min(0.38, (seeded(s + 6) * 0.2 + 0.15) * depthFactor),
        ),
      };
    });
  };

  const scattered = Array.from({ length: 80 }, (_, i) => {
    const s = 1000 + i * 13;
    const depth = seeded(s) * 200 - 50;
    const depthFactor = 1 + depth / 200;
    const top = seeded(s + 1) * 90;
    return {
      top: `${top}%`,
      left: `${seeded(s + 2) * 70 + 30}%`,
      size: (seeded(s + 3) * 2.5 + 0.8) * depthFactor,
      depth,
      delay: seeded(s + 4) * 5,
      duration: seeded(s + 5) * 3 + 2,
      opacity: Math.max(
        0.13,
        Math.min(0.32, (seeded(s + 6) * 0.16 + 0.14) * depthFactor),
      ),
    };
  });

  return [
    ...createCluster(60, 20, 60, 25, 1),
    ...createCluster(75, 40, 50, 20, 2),
    ...createCluster(55, 50, 45, 18, 3),
    ...createCluster(70, 70, 40, 22, 4),
    ...scattered,
  ]
    .filter((star, idx) => {
      const topValue = parseFloat(star.top);
      const leftValue = parseFloat(star.left);
      if (topValue > 90) return false;
      if (topValue < 30 && leftValue < 50) return false;
      if (leftValue < 50) return seeded(2000 + idx) > 0.5;
      return true;
    })
    .map((star, i) => ({ ...star, id: i }))
    .concat([
      { id: 999, top: "15%", left: "25%", size: 2, depth: -20, delay: 0, duration: 4, opacity: 0.2 },
      { id: 998, top: "22%", left: "18%", size: 1.5, depth: -30, delay: 1.5, duration: 5, opacity: 0.16 },
      { id: 997, top: "10%", left: "35%", size: 2.2, depth: -15, delay: 3, duration: 4.5, opacity: 0.18 },
      { id: 996, top: "9%", left: "92%", size: 1.8, depth: -18, delay: 0.8, duration: 4.6, opacity: 0.18 },
      { id: 995, top: "14%", left: "97%", size: 1.3, depth: -26, delay: 2.2, duration: 5.2, opacity: 0.15 },
      { id: 994, top: "19%", left: "89%", size: 2.1, depth: -12, delay: 3.6, duration: 4.1, opacity: 0.19 },
    ])
    .map((star) => ({
      ...star,
      topPct: styleNum(parseFloat(star.top)),
      leftPct: styleNum(parseFloat(star.left)),
      sizePx: styleNum(star.size),
      delayS: styleNum(star.delay),
      durationS: styleNum(star.duration),
      opacityStr: styleNum(star.opacity),
      boxShadow: `0 0 ${styleNum(star.size * 1.2)}px rgba(16, 185, 129, 0.16), 0 0 ${styleNum(star.size * 2.5)}px rgba(16, 185, 129, 0.08)`,
    }));
};

export { seeded, styleNum, buildStarList };
