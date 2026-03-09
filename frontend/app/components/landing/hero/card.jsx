"use client";

import Image from "next/image";

const Card = ({ isCardHovered, isCardClicked, onHoverChange, onCardClick }) => {
  const isStraight = isCardClicked || isCardHovered;
  const greenTheme = isStraight ? "hero-card-green-theme" : "";
  const transformClass = isStraight ? "hero-card-flat" : "hero-card-3d";
  const rayClass = isStraight ? "hero-card-ray-visible" : "";
  const ultraCloudClass = isStraight ? "hero-card-cloud-ultrawide-active" : "";

  return (
    <div
      className="group relative w-full max-w-sm sm:max-w-md lg:max-w-lg xl:max-w-xl mx-auto lg:mx-0 perspective-[2000px] cursor-pointer"
      onMouseEnter={() => onHoverChange(true)}
      onMouseLeave={() => onHoverChange(false)}
      onTouchStart={() => onHoverChange(true)}
      onTouchEnd={() => onHoverChange(false)}
      onClick={onCardClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onCardClick();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label="Toggle card view"
    >
      <div className={`hero-card ${greenTheme} ${transformClass}`}>
        <div className="absolute inset-0 p-1.5 sm:p-2 rounded-[18px] sm:rounded-[22px] overflow-hidden">
          <Image
            src="/images/hero.png"
            alt="Preview of a MeetNote meeting with participants, transcripts, and notes"
            width={1087}
            height={645}
            className="h-full w-full rounded-2xl object-cover"
            sizes="(min-width: 1280px) 520px, (min-width: 1024px) 460px, (min-width: 768px) 420px, 90vw"
            priority
          />
          <div className={`hero-card-image-overlay ${isStraight ? "hero-card-image-overlay-bright" : ""}`} />
        </div>
      </div>
      <div className={`hero-card-ray ${rayClass}`} />
      <div className={`hero-card-cloud-ultrawide ${ultraCloudClass}`} />
    </div>
  );
};

export default Card;
