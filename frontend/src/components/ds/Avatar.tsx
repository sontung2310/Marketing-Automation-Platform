import { useState } from "react";

import { cn } from "../../lib/cn";
import { initials } from "../../lib/format";

interface AvatarProps {
  name: string;
  src: string | null;
}

const FRAME = "h-3.5 w-3.5 flex-none rounded-full border border-border";

/**
 * Round profile image, falling back to the monogram when there is no image or
 * it fails to load. Decorative: the name or handle always sits beside it.
 */
export function Avatar({ name, src }: AvatarProps) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  if (src && src !== failedSrc) {
    return (
      <img
        src={src}
        alt=""
        loading="lazy"
        className={cn(FRAME, "bg-surface-muted object-cover")}
        onError={() => setFailedSrc(src)}
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className={cn(FRAME, "grid place-items-center text-small font-medium text-text-muted")}
    >
      {initials(name)}
    </span>
  );
}
