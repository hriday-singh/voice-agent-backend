import React from "react";
import { IconType } from "react-icons";

interface IconProps {
  icon: IconType;
  size?: string | number;
  color?: string;
  className?: string;
  style?: React.CSSProperties;
}

export const IconWrapper: React.FC<IconProps> = ({
  icon,
  size = "1em",
  color,
  className = "",
  style = {},
}) => {
  // Use type assertion to tell TypeScript this is a valid component
  return React.createElement(icon as any, {
    size,
    color,
    className,
    style,
  });
};
