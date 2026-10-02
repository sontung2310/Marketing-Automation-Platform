import { useState, type FormEvent } from "react";

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
 * Edits the terms that scope social listening. Validation is shown as text, and
 * the canonical list always comes back from the API (api-contract,
 * `PUT /company/tracked-keywords`).
 */
export function TrackedKeywordEditor({ keywords }: TrackedKeywordEditorProps) {
  const [term, setTerm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const save = useSaveTrackedKeywords();
  const current = save.data?.tracked_keywords ?? keywords;

  const replace = (next: string[]) => {
    setError(null);
    save.mutate(next, {
      onError: (cause) => setError(cause instanceof ApiError ? cause.message : "Save failed."),
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
    <div className="flex flex-col gap-1 border-b border-border-strong px-2 pt-1 pb-2">
      <ul className="flex flex-wrap gap-1">
        {current.map((keyword) => (
          <li
            key={keyword}
            className="inline-flex h-3.5 items-center gap-0.5 rounded-sm bg-primary-light pr-0.5 pl-1 text-small font-semibold text-primary-hover"
          >
            {keyword}
            <Button
              variant="icon"
              aria-label={`Stop tracking ${keyword}`}
              className="h-2.5 w-2.5 text-primary-hover"
              disabled={current.length === 1 || save.isPending}
              onClick={() => replace(current.filter((value) => value !== keyword))}
            >
              <Icon name="close" size={12} />
            </Button>
          </li>
        ))}
      </ul>

      <form onSubmit={add} className="flex items-end gap-1">
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

      <p className="text-small text-text-muted">
        Scopes the social data we collect. The competitor feed is not filtered.
      </p>
    </div>
  );
}
