"""Helpers for extracting final text from A2A responses with artifacts."""

from a2a.utils.message import get_message_text


def extract_final_text(response: object) -> str:
    """Return the final task message instead of a preceding Canvas artifact."""
    events = getattr(response, "event", ())
    if not isinstance(events, (tuple, list)):
        events = (events,)
    for event in reversed(events):
        history = getattr(event, "history", None) or ()
        for message in reversed(history):
            try:
                text = get_message_text(message).strip()
            except Exception:
                continue
            if text:
                return text

    last_message = getattr(response, "last_message", None)
    text = getattr(last_message, "text", "")
    return text.strip() if isinstance(text, str) else str(response)
