interface LiveRegionProps {
  /** Announced politely when it changes (ui-spec §6). */
  message: string;
}

export function LiveRegion({ message }: LiveRegionProps) {
  return (
    <span role="status" aria-live="polite" className="sr-only">
      {message}
    </span>
  );
}
