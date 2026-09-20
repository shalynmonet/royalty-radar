"""Draft outreach emails for a track flagged as AI-generated.

Drafts only: nothing here is ever sent. Text in [brackets] is for the user to
fill in before sending anything.
"""

SENDERS = ("artist", "label")

# Origin values the API returns that carry no information about where a track came from.
NO_ORIGIN = {"", "unknown", "none", "n/a", "human"}


def usable_origin(result):
    """The detector's guess at the generating tool, or None if it gave no real answer."""
    origin = result.get("origin")
    if origin and str(origin).strip().lower() not in NO_ORIGIN:
        return str(origin).strip()
    return None

ARTIST_TEMPLATE = """Subject: A question about your track "[Track title]"

Hi [Their name],

I'm [Your name], an independent artist. A scan of the audio in "[Track title]" ([link to the post]) flagged it as likely AI-generated ({flagged}). Detection like this is probabilistic, so I may be wrong, which is why I'm asking.

If AI tools were used, and my music or voice was part of what they were trained on or styled after, I'd like to talk about credit, consent and revenue share. Could you tell me how the track was made and which tools you used?

I'd rather work this out directly than as a dispute. Thanks for your time.

[Your name]
[Contact details]"""

LABEL_TEMPLATE = """Subject: Inquiry regarding "[Track title]" ([Label name] / [Artist name])

Hello [Their name],

I'm [Your name] at [Label name], writing on behalf of our artist [Artist name]. An audio analysis of "[Track title]" ([link to the post]) flagged it as likely AI-generated ({flagged}). This is a probabilistic result, not a finding, and we are reaching out to understand, not to assume.

Could you let us know:
1. Whether AI tools were used to make the track, and which ones.
2. Whether any of [Artist name]'s recordings, vocals or compositions were used as input, reference or training material.
3. Where the track is published or monetized.

If our artist's work was involved, we would like to discuss consent, credit and a fair revenue share, and we are glad to set up a call. This message is an inquiry only and does not waive any rights of [Label name] or [Artist name].

Best regards,
[Your name], [Title], [Label name]
[Contact details]"""


def generate_outreach_email(result, sender="artist"):
    """sender is "artist" (an independent artist, first person) or "label"
    (a label representative writing for an artist)."""
    if sender not in SENDERS:
        raise ValueError(f"sender must be one of {SENDERS}")
    confidence = (result.get("confidence") or 0) * 100
    flagged = f"{confidence:.0f}% confidence"
    origin = usable_origin(result)
    if origin:
        flagged = f"possible origin: {origin}, {flagged}"
    template = LABEL_TEMPLATE if sender == "label" else ARTIST_TEMPLATE
    return template.replace("{flagged}", flagged)
