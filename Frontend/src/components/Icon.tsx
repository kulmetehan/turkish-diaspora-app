import * as React from "react";
import * as Icons from "lucide-react";

type LucideIcon = keyof typeof Icons;

export interface IconProps extends React.SVGProps<SVGSVGElement> {
  name: LucideIcon;
  sizeRem?: number;
  title?: string;
  decorative?: boolean;
}

export function Icon({ name, sizeRem = 1, title, decorative = true, ...rest }: IconProps) {
  const Cmp = Icons[name] as React.ComponentType<any>;
  if (!Cmp) return null;
  const ariaHidden = decorative ? true : undefined;
  const ariaLabel = !decorative && title ? title : undefined;

  return (
    <Cmp
      width={`${sizeRem}rem`}
      height={`${sizeRem}rem`}
      aria-hidden={ariaHidden}
      aria-label={ariaLabel}
      role={decorative ? "img" : "img"}
      {...rest}
    />
  );
}
