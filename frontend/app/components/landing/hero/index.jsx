"use client";

import { useState, useEffect } from "react";
import Background from "./background";
import Starfield from "./starfield";
import Content from "./content";
import Card from "./card";

function HeroSection({ onOpenAuth }) {
  const [isCardHovered, setIsCardHovered] = useState(false);
  const [isCardClicked, setIsCardClicked] = useState(false);
  const [windowWidth, setWindowWidth] = useState(0);

  useEffect(() => {
    let rafId = null;
    const handleResize = () => {
      if (rafId !== null) return;
      rafId = requestAnimationFrame(() => {
        setWindowWidth(window.innerWidth);
        rafId = null;
      });
    };
    setWindowWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  }, []);

  const isDesktop = windowWidth >= 1024;
  const isTablet = windowWidth >= 640 && windowWidth < 1024;

  return (
    <section className="relative flex w-full items-center overflow-hidden min-h-screen perspective-[1200px]">
      <Background
        isDesktop={isDesktop}
        isTablet={isTablet}
        isCardHovered={isCardHovered}
        isCardClicked={isCardClicked}
      />
      <Starfield />
      <div className="relative z-10 mx-auto flex w-full max-w-6xl items-center px-4 pt-4 pb-6 sm:px-6 sm:pt-5 sm:pb-8 md:pt-8 md:pb-12 lg:max-w-7xl lg:pt-10 lg:pb-16 xl:px-10">
        <div className="flex w-full flex-col gap-5 sm:gap-6 lg:gap-8 lg:flex-row lg:items-center">
          <Content onOpenAuth={onOpenAuth} />
          <Card
            isCardHovered={isCardHovered}
            isCardClicked={isCardClicked}
            onHoverChange={setIsCardHovered}
            onCardClick={() => setIsCardClicked((prev) => !prev)}
          />
        </div>
      </div>
    </section>
  );
}

export default HeroSection;
