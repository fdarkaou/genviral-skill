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
Upload a file to genviral's CDN using the presigned URL flow. Returns a CDN URL you can use in posts.

```bash
genviral upload --file video.mp4 --content-type video/mp4
genviral upload --file slide1.jpg --content-type image/jpeg --filename "slide1.jpg"
```

Supported content types:
- Videos: `video/mp4`, `video/quicktime`, `video/x-msvideo`, `video/webm`, `video/x-m4v`
- Images: `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `image/heic`, `image/heif`

Returns the CDN URL (use in create-post).

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
