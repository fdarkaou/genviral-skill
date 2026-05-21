# Post Commands

Canonical Partner API docs (field names, limits, errors):

- [Create Post](https://docs.genviral.io/api-reference/create-post)
- [Update Post](https://docs.genviral.io/api-reference/update-post)
- [Get Accounts](https://docs.genviral.io/api-reference/get-accounts)
- Machine-readable index: [llms.txt](https://docs.genviral.io/llms.txt)

Run `genviral accounts` first. Use each account's `capabilities.supported_content_kinds` and `caption_limit` before building a payload. `capabilities.settings_schema` reflects the dashboard composer and may differ from Partner API field names — use the tables below for create payloads.

---

## create-post

Create a video, slideshow, or text-only post for one or more accounts (max 10).

### Video

```bash
genviral create-post \
  --caption "Your caption with #hashtags" \
  --media-type video \
  --media-url "https://cdn.genviral.com/your-video.mp4" \
  --duration-sec 42 \
  --accounts "account_id_1,account_id_2" \
  --scheduled-at "2026-05-21T15:00:00Z" \
  --external-id "my-campaign-001"
```

Video metadata (optional but recommended): `--duration-sec`, `--duration-seconds`, `--duration`, `--durationSec`, `--video-duration-sec`, `--bytes`, `--size`, `--width`, `--height`, `--mime-type`, `--metadata-json`.

- **Non-premium X video:** `--duration-sec` is required; max 140 seconds.
- **Hosted accounts:** when duration is provided, enforce 15–60 seconds.

### Slideshow

```bash
genviral create-post \
  --caption "Your caption" \
  --media-type slideshow \
  --media-urls "url1,url2,url3,url4,url5,url6" \
  --accounts "account_id_1" \
  --music-url "https://www.tiktok.com/@user/video/1234567890"
```

1–35 JPG/JPEG/PNG URLs, each under 5MB.

### Text-only

Omit `--media-type` and media URLs when **every** selected account supports `text_only` in `capabilities.supported_content_kinds`.

```bash
genviral create-post \
  --caption "Ship the repeatable thing, not the busywork." \
  --accounts "x_account_id" \
  --settings-json '{"x":{"who_can_reply_post":"everyone"}}'
```

### Scheduling

- Omit `--scheduled-at` or set a time within **30 seconds of now** → immediate publish queue (`status: pending`).
- True schedule → ISO 8601 **with timezone offset**, at least **2 minutes** in the future (`status: scheduled`).
- Example: `2026-05-21T15:00:00Z`

### Idempotency

`--external-id` (max 128 chars): same key + same payload replays the original post (`200`, `duplicate: true`). Same key + different payload → `409 create_failed`. If omitted, the API dedupes from a SHA-256 fingerprint of the body; conflicting replays also return `409 create_failed`.

### Provider settings layout

| Provider(s) | Create payload location | CLI first-class flags |
| --- | --- | --- |
| TikTok | Top-level `tiktok` | `--tiktok-*`, `--auto-add-music`, etc. |
| Pinterest | Top-level `pinterest` | `--pinterest-*` |
| YouTube | `settings.youtube` | `--youtube-title`, `--youtube-description`, `--youtube-type` |
| Instagram | `settings.instagram` or `settings.instagram-standalone` | `--instagram-post-type`, `--instagram-cover-url`, `--instagram-thumb-offset-ms`, `--instagram-share-to-feed`, etc. |
| X | `settings.x` | `--x-who-can-reply`, `--x-made-with-ai`, `--x-paid-partnership`, `--x-community` |
| Facebook, LinkedIn, Bluesky | `settings.<provider>` | `--settings-json` / `--settings-file` |

On **update**, use top-level `tiktok` / `pinterest` (CLI `--tiktok-*` / `--pinterest-*`, or `--clear-tiktok` / `--clear-pinterest`). Do not put TikTok or Pinterest under `settings` — same rule as create.

Only include settings for providers you are actually targeting. Unknown `settings` keys → `422 invalid_payload`.

**Do not** put TikTok or Pinterest under `settings` on create — use top-level `tiktok` / `pinterest` (or CLI flags). The CLI maps flags to top-level objects.

TikTok and Pinterest blocks can appear in the **same** request when you target multiple platforms (CLI sends both top-level objects).

---

### TikTok — top-level `tiktok` (BYO only)

Only when **all** accounts are TikTok BYO. Hosted TikTok rejects TikTok-specific settings. Requires media (video or slideshow).

For **video** posts, merged `caption` + `tiktok.title` + `tiktok.description` must stay **≤ 2,200 characters combined**.

```bash
genviral create-post \
  --caption "Caption" \
  --media-type slideshow \
  --media-urls "url1,url2,url3" \
  --accounts "tiktok_byo_account_id" \
  --tiktok-title "Optional title" \
  --tiktok-description "Optional description" \
  --tiktok-post-mode "MEDIA_UPLOAD" \
  --tiktok-privacy "SELF_ONLY" \
  --tiktok-disable-comment \
  --auto-add-music true \
  --is-your-brand false \
  --is-branded-content false
```

| Field | CLI flag | Notes |
| --- | --- | --- |
| `title` | `--tiktok-title` | Video: max 2,200 chars. Slideshow: max 90 chars. |
| `description` | `--tiktok-description` | Slideshow: max 4,000. Video: publish body when `caption` empty. |
| `post_mode` | `--tiktok-post-mode` | `DIRECT_POST` (default) or `MEDIA_UPLOAD` (slideshow drafts only). |
| `privacy_level` | `--tiktok-privacy` | `PUBLIC_TO_EVERYONE`, `MUTUAL_FOLLOW_FRIENDS`, `FOLLOWER_OF_CREATOR`, `SELF_ONLY`. |
| `disable_comment` | `--tiktok-disable-comment` | Boolean; flag form sets `true`. |
| `disable_duet` | `--tiktok-disable-duet` | Video only. |
| `disable_stitch` | `--tiktok-disable-stitch` | Video only. |
| `auto_add_music` | `--auto-add-music` | Slideshow only. |
| `is_your_brand` | `--is-your-brand` | Own-brand commercial. |
| `is_branded_content` | `--is-branded-content` | Third-party promotion. |
| `user_consent` | `--user-consent` | Policy consent. |
| `is_commercial` | `--is-commercial` | Commercial flag. |
| `video_cover_timestamp_ms` | `--tiktok-video-cover-timestamp-ms` | Video `DIRECT_POST` only. Frame offset in ms for the TikTok thumbnail. |

Boolean toggles accept `--flag` (true) or `--flag false`.

**Draft timing:** `MEDIA_UPLOAD` + `pending` is normal until the worker runs (~5 min). Check account states before assuming failure.

**Draft cap:** CLI blocks at 5+ `MEDIA_UPLOAD` uploads per account in 24h. Override: `--force-media-upload-cap`.

`--music-url` must be a TikTok post URL. Rejected when any non-TikTok account is selected (including Instagram).

---

### Pinterest — top-level `pinterest`

When at least one account is Pinterest. Requires image media (slideshow).

```bash
genviral create-post \
  --caption "Minimal kitchen organization ideas" \
  --media-type slideshow \
  --media-urls "https://cdn.example.com/pin-cover.jpg" \
  --accounts "pinterest_account_id" \
  --pinterest-board-id "YOUR_BOARD_ID" \
  --pinterest-title "Pin title" \
  --pinterest-link "https://example.com/guide" \
  --pinterest-tags "kitchen organization,home tips"
```

| Field | CLI flag | Notes |
| --- | --- | --- |
| `board_id` | `--pinterest-board-id` | **Required** for a successful pin publish. **No account default.** Max 128 chars. |
| `title` | `--pinterest-title` | Optional; max 100 chars. |
| `link` | `--pinterest-link` | Optional destination URL; max 2,048 chars. |
| `tags` | `--pinterest-tags` | Comma-separated; up to 30 tags, 1–100 chars each. Appended to description; total ≤ 800 chars. |

---

### YouTube — `settings.youtube` (video required)

```bash
genviral create-post \
  --caption "Weekly product recap and what shipped." \
  --media-type video \
  --media-url "https://cdn.example.com/recap.mp4" \
  --duration-sec 42 \
  --accounts "youtube_account_id" \
  --settings-json '{"youtube":{"title":"Weekly product recap","type":"public"}}'
```

| Field | Notes |
| --- | --- |
| `title` | Max 100 chars. If omitted: `settings.youtube.description`, then first non-empty `caption` line. |
| `description` | Overrides `caption` as YouTube description when set. |
| `type` / `privacy` | `public`, `private`, `unlisted`. Default `public`. |
| `tags` | `[{ "value": "...", "label": "..." }]` — publish uses `label`. |
| `categoryId` | YouTube category ID. |
| `selfDeclaredMadeForKids` | `yes` or `no` (default `no`). Alias: `madeForKids` boolean. |
| `thumbnail` | `{ "path": "<image-url>" }` |

---

### X — `settings.x` or `settings.twitter`

```bash
genviral create-post \
  --caption "Quick take on the launch." \
  --accounts "x_account_id" \
  --settings-json '{"x":{"who_can_reply_post":"everyone","made_with_ai":false,"paid_partnership":false}}'
```

| Field | Notes |
| --- | --- |
| `who_can_reply_post` | `everyone` (default), `following`, `mentionedUsers`, `subscribers`, `verified`. |
| `community` | `https://x.com/i/communities/<id>` |
| `made_with_ai` | Default `false`. |
| `paid_partnership` | Default `false`. |

Caption limit: 280 (4,000 for premium X accounts).

---

### Instagram — `settings.instagram` or `settings.instagram-standalone`

Both keys map to the same storage; if both sent, `instagram-standalone` wins.

```bash
genviral create-post \
  --caption "Behind the scenes from today's shoot." \
  --media-type video \
  --media-url "https://cdn.example.com/reel.mp4" \
  --accounts "instagram_account_id" \
  --instagram-post-type post \
  --instagram-cover-url "https://cdn.example.com/reel-cover.jpg" \
  --instagram-share-to-feed false
```

| Field | CLI flag | Notes |
| --- | --- | --- |
| `post_type` | `--instagram-post-type` | Recommended: `post` (feed/reel) or `story`. |
| `is_trial_reel` | `--instagram-trial-reel` | Trial reel flag for video. |
| `graduation_strategy` | `--instagram-graduation-strategy` | `MANUAL` or `SS_PERFORMANCE` with trial reels. |
| `collaborators` | `--instagram-collaborators` | Comma-separated usernames → `[{ "label": "..." }]`. Ignored for stories. |
| `cover_url` | `--instagram-cover-url` | Custom Reel cover image URL. Takes priority over `thumb_offset_ms`. Video + `post_type: post` only. Must be publicly accessible. **BYO Instagram only.** |
| `thumb_offset_ms` | `--instagram-thumb-offset-ms` | Reel frame thumbnail offset in ms when no `cover_url`. Video + `post_type: post` only. **BYO Instagram only.** |
| `share_to_feed` | `--instagram-share-to-feed` | Share Reel to main feed. Default `true`. Set `false` for Reels tab only. **BYO Instagram only.** |

Do not use `--music-url` with Instagram accounts (TikTok-only).

---

### Facebook — `settings.facebook`

```bash
--settings-json '{"facebook":{"url":"https://example.com/article"}}'
```

| Field | Notes |
| --- | --- |
| `url` | Optional link attachment on the post. |

---

### LinkedIn — `settings.linkedin` or `settings.linkedin-page`

If both sent, `linkedin-page` wins.

```bash
--settings-json '{"linkedin":{"post_as_images_carousel":true,"carousel_name":"Q1 highlights"}}'
```

| Field | Notes |
| --- | --- |
| `post_as_images_carousel` | Multi-image as carousel/PDF. |
| `carousel_name` | Title; default `slides`. |

---

### Bluesky — `settings.bluesky`

No provider-specific fields. Omit or send `{}`:

```bash
--settings-json '{"bluesky":{}}'
```

---

### Multi-account rules

- Up to 10 accounts per post.
- `--music-url` only when **all** accounts are TikTok.
- TikTok-specific flags only when **all** accounts are TikTok BYO.
- Pinterest flags when at least one Pinterest account is targeted.
- Mix platforms with `--settings-json` for non-TikTok/Pinterest providers plus top-level TikTok/Pinterest as needed.

### Draft / analytics IDs

`create-post` returns the Genviral post ID immediately. BYO TikTok `MEDIA_UPLOAD` is not the public TikTok video ID until published in the TikTok app. Correlate later via `genviralPostId` or `externalId` in `analytics-posts` — see `docs/api/analytics.md`.

---

## update-post

Only `draft`, `pending`, `scheduled`, `retry`, or `failed` posts are editable.

```bash
genviral update-post \
  --id POST_ID \
  --caption "Updated caption" \
  --media-type video \
  --media-url "https://new-video.mp4" \
  --accounts "new_account_id_1,new_account_id_2" \
  --scheduled-at "2026-05-21T18:00:00Z"
```

Clear / null operations:

- Remove music: `--music-url null`
- Publish ASAP: `--clear-scheduled-at` (sets `scheduled_at` to `null` → `pending`)
- Clear TikTok settings: `--clear-tiktok`
- Clear Pinterest settings: `--clear-pinterest`

Provider settings on update:

```bash
genviral update-post \
  --id POST_ID \
  --instagram-cover-url "https://cdn.example.com/new-cover.jpg" \
  --instagram-share-to-feed false
```

Partial Instagram patches merge with stored settings — updating only `--instagram-share-to-feed` keeps an existing `--instagram-cover-url`.

- `--instagram-*`, `--youtube-*`, and `--x-*` flags work on update the same as create.
- `--settings-json` / `--settings-file` — partial `settings` patch for other providers.
- TikTok/Pinterest — same flags as create, or `--clear-tiktok` / `--clear-pinterest`.
- `external_id` is **immutable** after create; changing it returns `409 external_id_immutable`.
- At least one field required; empty body → `422 invalid_payload`.
- `media: null` (omit `--media-type` and pass text-only only if accounts support it).

---

## retry-posts

```bash
genviral retry-posts --post-ids "post_id_1,post_id_2"
genviral retry-posts --post-ids "post_id_1" --account-ids "account_id_1"
```

Limits: `post_ids` 1–20; `account_ids` 1–10.

---

## list-posts

```bash
genviral list-posts
genviral list-posts --status scheduled --limit 20
genviral list-posts --since "2026-02-01T00:00:00Z" --until "2026-02-28T23:59:59Z"
genviral list-posts --json
```

`--since` / `--until` require timezone offsets.

Status filters: `draft`, `pending`, `scheduled`, `posted`, `failed`, `partial`, `retry`, `canceled`

---

## get-post

```bash
genviral get-post --id POST_ID
```

---

## delete-posts (alias: `delete-post`)

```bash
genviral delete-posts --ids "post_id_1,post_id_2,post_id_3"
```

Up to 50 IDs. Returns `deletedIds`, `blockedStatuses`, `skipped`, `errors`.

---

## Post API errors (quick reference)

| Code | When |
| --- | --- |
| `422 invalid_payload` | Schema/enum failure (`issues` array) |
| `400 validation_failed` | Caption, media, music, TikTok/Pinterest, schedule, immutable post |
| `400 unknown_accounts` | Account outside key scope |
| `400 media_unreachable` | Media URL not reachable |
| `400 invalid_music_url` | Not a TikTok URL or used with Instagram |
| `401` | Invalid/missing API key |
| `402 subscription_required` | No Creator/Professional/Business plan |
| `403 subscription_required` | Hosted TikTok without virtual subscription |
| `403 tier_not_allowed` | Scheduler tier |
| `409 create_failed` | Same `--external-id` or dedupe fingerprint, different create payload |
| `409 external_id_immutable` | PATCH tried to change `external_id` |
| `404 not_found` | Post outside scope (get/update) |
| `500 create_failed` / `500 update_failed` | Unexpected failure |

See `docs/api/errors.md` for CLI and cross-command troubleshooting.
