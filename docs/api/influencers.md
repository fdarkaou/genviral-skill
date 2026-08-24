# Influencer Commands

Influencers are consistent characters: one or more reference images of a person,
reused to generate new images of that person. The API does not distinguish how
the character was created.

**Always list before generating UGC.** Pass returned `reference_image_urls` to
`studio-generate-image --image-urls`.

---

## list-influencers

List influencers in the current key scope, newest created first.

```bash
genviral list-influencers
genviral list-influencers --limit 20
genviral list-influencers --json
```

Options:
- `--limit`: 1–50, default 20
- `--json`: raw JSON output

Returns: `influencers[]` with `id`, `name`, `reference_image_urls`, plus `has_more`.

---

## get-influencer

Fetch one influencer and its reference images.

```bash
genviral get-influencer --id INFLUENCER_UUID
genviral get-influencer --id INFLUENCER_UUID --json
```

Errors:
- `404 not_found` — missing or not visible in this scope
- `422 invalid_path` — `--id` is not a UUID

---

## Using an influencer in Studio

```bash
genviral studio-generate-image \
  --model-id "openai/gpt-image-2" \
  --prompt "The same person holding a coffee cup in a sunny kitchen" \
  --image-urls "https://cdn.example.com/maya.jpg"
```

Use every URL from `reference_image_urls` when the model accepts multiple
reference images.
