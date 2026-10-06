import { useEffect, useRef, useState, type FormEvent } from "react";

import { ApiError } from "../../api";
import { Button } from "../../components/ds/Button";
import { Icon } from "../../components/ds/Icon";
import { TextInput } from "../../components/ds/TextInput";
import { useSaveTrackedKeywords } from "../../hooks/queries";

const MAX_KEYWORDS = 20;

interface TrackedKeywordEditorProps {
  keywords: string[];
}

/**
 * Edits the terms that scope social listening, one row per term. Validation is
 * shown as text, and the canonical list always comes back from the API
 * (api-contract, `PUT /company/tracked-keywords`).
 */
export function TrackedKeywordEditor({ keywords }: TrackedKeywordEditorProps) {
  const [adding, setAdding] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  const [term, setTerm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const save = useSaveTrackedKeywords();
  const current = save.data?.tracked_keywords ?? keywords;

  // Opening the form is an explicit request to type, so focus follows it.
  useEffect(() => {
    if (adding) form.current?.querySelector("input")?.focus();
  }, [adding]);

  const replace = (next: string[]) => {
    setError(null);
    save.mutate(next, {
      onError: (cause) => {
        setAdding(true); // the message lives in the form, so keep it on screen
        setError(cause instanceof ApiError ? cause.message : "Save failed.");
      },
    });
  };

  const add = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = term.trim();
    if (!trimmed) {
      setError("Enter a keyword to track.");
      return;
    }
    if (current.some((keyword) => keyword.toLocaleLowerCase() === trimmed.toLocaleLowerCase())) {
      setError(`"${trimmed}" is already tracked.`);
      return;
    }
    if (current.length >= MAX_KEYWORDS) {
      setError(`Track at most ${MAX_KEYWORDS} keywords.`);
      return;
    }
    setTerm("");
    replace([...current, trimmed]);
  };

  return (
    <div className="flex flex-col gap-1 border-b border-border px-2 pt-1.5 pb-2">
      <div className="flex h-3 items-center justify-between">
        <span className="text-small text-text-muted">Tracked keywords</span>
        <Button
          variant="quiet"
          aria-expanded={adding}
          onClick={() => setAdding((value) => !value)}
          size="sm"
          className="gap-0.5"
        >
          <Icon name="plus" size={12} />
          Add keyword
        </Button>
      </div>

      {adding ? (
        <form ref={form} onSubmit={add} className="flex items-end gap-1">
          <TextInput
            label="Add a tracking keyword"
            labelHidden
            placeholder="Add a keyword"
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            error={error ?? undefined}
            className="flex-1"
          />
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Add"}
          </Button>
        </form>
      ) : null}

      <ul className="overflow-hidden rounded-md border border-border">
        {current.map((keyword) => (
          <li
            key={keyword}
            className="group grid h-4.5 layout-keyword-row items-center gap-1 border-t border-border bg-surface-card pr-1 pl-1.5 transition-colors first:border-t-0 hover:bg-surface-muted"
          >
            <span
              aria-hidden="true"
              className="text-accent grid h-2.5 w-2.5 place-items-center rounded-sm bg-primary-light text-small font-medium"
            >
              #
            </span>
            <span className="truncate text-small font-medium text-text">{keyword}</span>
            <Button
              variant="icon"
              aria-label={`Stop tracking ${keyword}`}
              size="sm"
              className="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
              disabled={current.length === 1 || save.isPending}
              onClick={() => replace(current.filter((value) => value !== keyword))}
            >
              <Icon name="close" size={12} />
            </Button>
          </li>
        ))}
      </ul>

      <p className="text-small text-text-muted">
        Scopes the social data we collect. The competitor feed is not filtered.
      </p>
    </div>
  );
}
