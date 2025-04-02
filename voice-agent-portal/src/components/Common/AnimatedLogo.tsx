import React, { useRef } from "react";
import useImagePreload from "../../hooks/useImagePreload";

interface AnimatedLogoProps {
  className?: string;
  height?: number;
  width?: number;
  gifSrc: string;
  fallbackSrc: string;
  alt: string;
  onClick?: () => void;
}

const AnimatedLogo: React.FC<AnimatedLogoProps> = ({
  className = "",
  height,
  width,
  gifSrc,
  fallbackSrc,
  alt,
  onClick,
}) => {
  // Preload both images to ensure they're cached
  useImagePreload(gifSrc);
  useImagePreload(fallbackSrc);

  const imgRef = useRef<HTMLImageElement>(null);

  return (
    <div className={`animated-logo ${className}`}>
      <img
        ref={imgRef}
        src={gifSrc}
        alt={alt}
        style={{ height, width }}
        onError={(e) => {
          // Fallback to static logo if GIF doesn't load
          const target = e.target as HTMLImageElement;
          target.src = fallbackSrc;
        }}
        onClick={onClick}
        // Adding fetchpriority and loading attributes for better performance
        // @ts-ignore - fetchpriority is a new attribute not yet in typings
        fetchpriority="high"
        loading="eager"
      />
    </div>
  );
};

export default AnimatedLogo;
