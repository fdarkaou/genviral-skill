# API Error Codes & Troubleshooting

## Common Error Codes

- `401 unauthorized` - API key missing, malformed, or invalid
- `402 subscription_required` - workspace needs an active Creator, Professional, or Business subscription
- `403 tier_not_allowed` - Scheduler tier cannot use Partner API
- `403 subscription_required` - hosted TikTok posting without active TikTok virtual subscription
- `422 invalid_payload` - request shape, unknown `settings` keys, or enum values invalid (`issues` array on posts)
- `429 rate_limited` - too many requests in a short window

---

## Post commands (`create-post`, `update-post`)

| Code | When |
| --- | --- |
| `400 validation_failed` | Caption/media limits, schedule under 2 min ahead, TikTok/Pinterest rules, immutable post status, text-only on media-required accounts |
| `400 unknown_accounts` | Account UUID not in API key scope |
| `400 missing_accounts` | Resolved account list empty (update) |
| `400 media_unreachable` | Video/slideshow URL not fetchable |
| `400 invalid_music_url` | Not a TikTok URL, or `music_url` with Instagram/non-TikTok accounts |
| `409 create_failed` | Same `--external-id` or dedupe fingerprint reused with a different create body |
| `409 external_id_immutable` | `update-post` tried to change `external_id` |
| `404 not_found` | Post ID outside key scope |
| `500 create_failed` / `500 update_failed` | Unexpected upstream failure |

**Pinterest:** missing `board_id` / `--pinterest-board-id` does not fall back to an account default — pin publish needs an explicit board ID.

**Scheduling:** future `scheduled_at` must be ISO 8601 with offset and at least 2 minutes ahead; immediate queue = omit or within ~30 seconds of now.

**Settings:** on create, use top-level `tiktok` / `pinterest` (CLI flags), not `settings.tiktok` / `settings.pinterest`. Other providers use `settings.<provider>` via `--settings-json`.

Canonical field tables: [Create Post](https://docs.genviral.io/api-reference/create-post), [Update Post](https://docs.genviral.io/api-reference/update-post).

---

## Troubleshooting

**"GENVIRAL_API_KEY is required"**
Export the environment variable: `export GENVIRAL_API_KEY="your_public_id.your_secret"`

**"No rendered image URLs found"**
The slideshow has not been rendered yet. Run `render` first.

**API returns 401, 402, or 403**
- `401`: verify API key format (`public_id.secret`) and token validity
- `402 subscription_required`: activate or upgrade subscription
- `403 tier_not_allowed`: your tier does not permit Partner API posting

**`create-post` / `update-post` returns 422**
- Check `--settings-json` is valid JSON and uses Partner API keys (e.g. `instagram`, not dashboard-only names like `coverUrl`)
- Instagram Reel cover fields: `--instagram-cover-url`, `--instagram-thumb-offset-ms`, `--instagram-share-to-feed` (BYO Instagram + video only)
- Unknown provider under `settings` → `422 invalid_payload`
- `update-post` with no fields → provide at least one patch field

**`create-post` returns 409**
- Reused `--external-id` or body fingerprint with different caption/media/accounts → `409 create_failed`

**Render takes too long**
Each slide takes 2-5 seconds. For 5 slides, expect up to 25 seconds.

**`update-slideshow` returns 422**
- Check for `null` values (omit fields instead of setting `null`)
- Check that `background_filters` has all 10 sub-fields
- Check that no slide has an `index` field
- Check that every slide has at minimum `image_url` and `text_elements`
