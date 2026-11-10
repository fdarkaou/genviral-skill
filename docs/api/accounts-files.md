# Account & File Commands

> **Organizing files?** Use folders to group uploads and Studio-generated assets.
> See `docs/api/folders.md` for `create-folder`, `list-folders`, `folder-items-add`, etc.

## accounts
List connected BYO and hosted accounts in your scope. Use this to discover account IDs for posting.

```bash
genviral accounts
genviral accounts --json
```

Returns per account:
- `id` — UUID for `--accounts` on `create-post`
- `platform` (tiktok, instagram, twitter, youtube, pinterest, etc.)
- `type` — `byo` or `hosted`
- `username`, `display_name`, `status`
- `capabilities.supported_content_kinds` — e.g. `text_only`, `single_video`, `multi_image`
- `capabilities.caption_limit` — max caption length for that account
- `capabilities.media_limits` — e.g. `max_images`, `max_video_seconds`
- `capabilities.settings_schema` — dashboard composer schema; **for create payloads use** [Create Post](https://docs.genviral.io/api-reference/create-post) **field tables**, not `settings_schema` alone

Hosted accounts: caption cap 500 chars; usually no `text_only`. TikTok hosted cannot use BYO-only `tiktok` settings.

## upload
Upload a file to genviral's CDN. The CLI runs the full flow (prepare, PUT, finalize) and prints
the finalized file. Use `file.url` in posts, slideshows, and Studio `--image-urls`.

`--idempotency-key` is required (max 255 chars). Use a new key per file; reuse a key only to
retry the same upload.

```bash
genviral upload --file video.mp4 --content-type video/mp4 --idempotency-key "$(uuidgen)"
genviral upload --file slide1.jpg --content-type image/jpeg --filename "slide1.jpg" --idempotency-key "$(uuidgen)"
# → {"file": {"id": "...", "url": "https://cdn.vireel.io/verified-media/...", "contentType": "image/jpeg", ...}}
```

Requires `genviral` CLI 0.1.2 or later. The old `@genviral/cli` 0.1.1 skips finalize and returns no
usable URL.

Raw API flow (for scripts that call the REST API directly):

1. `POST /files` with header `Idempotency-Key` and body `{"contentType", "filename", "bytes"}`.
   The API answers `400 "Idempotency-Key is required"` without the header. The response has
   `data.id` and `data.uploadUrl`.
2. `PUT` the raw bytes to `data.uploadUrl` with the same `Content-Type`. No auth header.
3. `POST /files/{id}/finalize` with an `Idempotency-Key` header and **the same body as step 1**.
   The public URL is `data.file.url`.

Size limits: images 50 MB, videos 500 MB, audio 10 MB. One PUT carries at most 100 MB; above that
use `upload-multipart`.

Supported content types:
- Videos: `video/mp4`, `video/quicktime`, `video/x-msvideo`, `video/webm`, `video/x-m4v`
- Images: `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `image/heic`, `image/heif`
- Audio: `audio/mpeg`, `audio/wav`, `audio/ogg`, `audio/aac`, `audio/mp4`

**Downloading from the CDN:** `cdn.vireel.io` returns 403 to clients that send no browser-like
`User-Agent` (for example Python `urllib` defaults). Send a browser `User-Agent` header.

## list-files
List files uploaded via the Partner API.

```bash
genviral list-files
genviral list-files --type video --limit 20 --offset 0
genviral list-files --type image --context ai-studio,media-upload
genviral list-files --context all  # include all contexts
genviral list-files --json
```

`--type` accepts: `image` or `video`.
