"""The run input the model sees: intent, labelled untrusted trigger data, history, message."""

import json
from datetime import UTC, datetime

from app.agents.common.context import RunContext

UNTRUSTED = "UNTRUSTED_SOURCE_CONTENT"


def render_input(context: RunContext, message: str | None) -> str:
    # The model has no clock; staleness (> 21 days) needs today's date.
    parts = [f"Today: {datetime.now(UTC).date().isoformat()}", f"Intent: {context.intent}"]
    if context.trigger_context is not None:
        record = json.dumps(context.trigger_context, ensure_ascii=False, indent=1)
        parts.append(f"Trigger record:\n<{UNTRUSTED}>\n{record}\n</{UNTRUSTED}>")
    if context.previous_output is not None:
        previous = json.dumps(context.previous_output, ensure_ascii=False, indent=1)
        # It may quote third-party text, so it is data like the trigger record.
        parts.append(
            f"Your previous answer in this session:\n<{UNTRUSTED}>\n{previous}\n</{UNTRUSTED}>"
        )
    if message is not None:
        parts.append(f"User message:\n{message}")
    return "\n\n".join(parts)
