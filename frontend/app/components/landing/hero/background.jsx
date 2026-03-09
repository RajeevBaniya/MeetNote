"use client";

const Background = ({ isDesktop, isTablet, isCardHovered, isCardClicked }) => {
  const cardActive = isCardHovered || isCardClicked;

  const outerGradient = isDesktop
    ? "radial-gradient(ellipse 30% 100% at 78% 100%, rgba(16, 185, 129, 0.2) 0%, rgba(16, 185, 129, 0.18) 25%, rgba(16, 185, 129, 0.15) 50%, rgba(16, 185, 129, 0.1) 70%, transparent 90%)"
    : isTablet
      ? "radial-gradient(ellipse 35% 100% at 65% 100%, rgba(16, 185, 129, 0.2) 0%, rgba(16, 185, 129, 0.18) 25%, rgba(16, 185, 129, 0.15) 50%, rgba(16, 185, 129, 0.1) 70%, transparent 90%)"
      : "radial-gradient(ellipse 40% 100% at 50% 100%, rgba(16, 185, 129, 0.2) 0%, rgba(16, 185, 129, 0.18) 25%, rgba(16, 185, 129, 0.15) 50%, rgba(16, 185, 129, 0.1) 70%, transparent 90%)";

  const innerGradientBright = isDesktop
    ? "radial-gradient(ellipse 20% 85% at 74% 100%, rgba(16, 185, 129, 0.68) 0%, rgba(16, 185, 129, 0.38) 10%, rgba(16, 185, 129, 0.2) 25%, rgba(16, 185, 129, 0.12) 55%, transparent 75%)"
    : isTablet
      ? "radial-gradient(ellipse 24% 85% at 65% 100%, rgba(16, 185, 129, 0.68) 0%, rgba(16, 185, 129, 0.38) 10%, rgba(16, 185, 129, 0.2) 25%, rgba(16, 185, 129, 0.12) 55%, transparent 75%)"
      : "radial-gradient(ellipse 28% 85% at 50% 100%, rgba(16, 185, 129, 0.68) 0%, rgba(16, 185, 129, 0.38) 10%, rgba(16, 185, 129, 0.2) 25%, rgba(16, 185, 129, 0.12) 55%, transparent 75%)";

  const innerGradientDim = isDesktop
    ? "radial-gradient(ellipse 20% 85% at 74% 100%, rgba(16, 185, 129, 0.52) 0%, rgba(16, 185, 129, 0.3) 10%, rgba(16, 185, 129, 0.17) 25%, rgba(16, 185, 129, 0.12) 55%, transparent 75%)"
    : isTablet
      ? "radial-gradient(ellipse 24% 85% at 65% 100%, rgba(16, 185, 129, 0.52) 0%, rgba(16, 185, 129, 0.3) 10%, rgba(16, 185, 129, 0.17) 25%, rgba(16, 185, 129, 0.12) 55%, transparent 75%)"
      : "radial-gradient(ellipse 28% 85% at 50% 100%, rgba(16, 185, 129, 0.52) 0%, rgba(16, 185, 129, 0.3) 10%, rgba(16, 185, 129, 0.17) 25%, rgba(16, 185, 129, 0.12) 55%, transparent 75%)";

  return (
    <>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.25),transparent_55%)]" />
      <div
        className="hero-bottom-cloud hero-bottom-cloud-outer absolute bottom-12 sm:bottom-16 lg:bottom-20 left-0 right-0 h-24 sm:h-28 lg:h-32 pointer-events-none"
        style={{
          background: outerGradient,
          filter: isDesktop ? "blur(40px)" : isTablet ? "blur(32px)" : "blur(24px)",
          transform: isDesktop ? "translateZ(-50px)" : "none",
          transformStyle: isDesktop ? "preserve-3d" : "flat",
        }}
      />
      <div
        className="hero-bottom-cloud hero-bottom-cloud-inner absolute bottom-12 sm:bottom-16 lg:bottom-20 left-0 right-0 h-16 sm:h-18 lg:h-20 pointer-events-none transition-all duration-300 ease-out"
        style={{
          background: cardActive ? innerGradientBright : innerGradientDim,
          filter: isDesktop ? "blur(30px)" : isTablet ? "blur(24px)" : "blur(18px)",
          transform: isDesktop ? "translateZ(-40px)" : "none",
          transformStyle: isDesktop ? "preserve-3d" : "flat",
        }}
      />
    </>
  );
};

export default Background;
