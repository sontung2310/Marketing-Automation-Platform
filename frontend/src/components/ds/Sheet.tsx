import { useCallback, useEffect, useRef, type ReactNode } from "react";

import { useDismissable } from "../../hooks/useDismissable";
import { Button } from "./Button";
import { Icon } from "./Icon";

interface SheetProps {
  label: string;
  onClose: () => void;
  header: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}

/**
 * The 520px pop-out over the right rail (ui-spec §3). It is non-modal: the feed
 * behind it stays reachable, because evidence chips scroll to it.
 */
export function Sheet({ label, onClose, header, footer, children }: SheetProps) {
  const ref = useRef<HTMLElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => onClose(), [onClose]);
  useDismissable(true, ref, close);

  // Keyboard focus follows the sheet in, and returns to the row that opened it.
  useEffect(() => {
    const opener = document.activeElement;
    closeButton.current?.focus();
    return () => {
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);

  return (
    <aside
      ref={ref}
      role="dialog"
      aria-modal="false"
      aria-label={label}
      className="fixed top-10 right-3 bottom-3 z-20 flex sheet-width flex-col overflow-hidden rounded-md border border-border-strong bg-surface-card shadow-overlay"
    >
      <div className="flex h-6 flex-none items-center gap-1 border-b border-border px-2">
        {header}
        <Button
          ref={closeButton}
          variant="icon"
          aria-label="Close"
          onClick={onClose}
          className="ml-auto"
        >
          <Icon name="close" />
        </Button>
      </div>
      <div className="flex flex-1 scrollbar-thin flex-col gap-2 overflow-y-auto p-2">
        {children}
      </div>
      {footer ? (
        <div className="flex items-center gap-2 border-t border-border-strong p-2">{footer}</div>
      ) : null}
    </aside>
  );
}
