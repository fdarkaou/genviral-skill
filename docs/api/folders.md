# Folder Commands

Folders organize partner-scoped files and slideshows into nested hierarchies.

**Media types supported:**
- `ai_image` — images generated via Studio AI
- `ai_video` — videos generated via Studio AI
- `upload` — files uploaded via `genviral.sh upload`
- `slideshow` — slideshows created via `genviral.sh generate`

> **Scope rule:** folder visibility always matches the key scope.
> Workspace keys only see workspace folders; personal keys only see personal folders.

---

## list-folders
List folders at a given hierarchy level.

```bash
genviral.sh list-folders --media-type upload
genviral.sh list-folders --media-type slideshow --parent-folder-id FOLDER_UUID
genviral.sh list-folders --media-type ai_image --limit 20 --offset 0
genviral.sh list-folders --media-type upload --json
```

Options:
- `--media-type` (required): `ai_image`, `ai_video`, `upload`, or `slideshow`
- `--parent-folder-id`: list subfolders of this folder (omit for root-level)
- `--limit`: 1–100, default 50
- `--offset`: default 0
- `--json`: raw JSON output

Returns: folder summaries with `file_count`, `subfolder_count`, `preview_files`.

---

## create-folder
Create a folder (optionally nested under a parent).

```bash
genviral.sh create-folder --name "March Campaign" --media-type upload
genviral.sh create-folder --name "Q1 Slideshows" --media-type slideshow --parent-folder-id FOLDER_UUID
```

Options:
- `--name` (required): folder name, 1–255 chars
- `--media-type` (required): `ai_image`, `ai_video`, `upload`, or `slideshow`
- `--parent-folder-id`: nest inside this folder

Errors:
- `409 folder_name_conflict` — duplicate name at that location → use a different name

---

## get-folder
Fetch metadata for a single folder.

```bash
genviral.sh get-folder --id FOLDER_UUID
genviral.sh get-folder --id FOLDER_UUID --json
```

---

## move-folder
Move a folder to a new parent (or promote to root).

```bash
genviral.sh move-folder --id FOLDER_UUID --parent-folder-id NEW_PARENT_UUID
genviral.sh move-folder --id FOLDER_UUID --to-root   # moves to root level
```

Options:
- `--id` (required): folder to move
- `--parent-folder-id`: target parent folder
- `--to-root`: set `parent_folder_id` to null (promotes to root)

Errors:
- `409 folder_move_conflict` — can't move into self, a descendant, or a parent with a name conflict

---

## delete-folder
Delete a folder and all its nested contents (cascades to subfolders and items).

```bash
genviral.sh delete-folder --id FOLDER_UUID
```

> **Warning:** cascade delete removes all subfolders and their items. Items (files/slideshows) themselves are NOT deleted from the platform — only removed from the folder.

---

## folder-ancestors
Get the breadcrumb trail from root to a folder's immediate parent.

```bash
genviral.sh folder-ancestors --id FOLDER_UUID
genviral.sh folder-ancestors --id FOLDER_UUID --json
```

Returns: ordered list of ancestor folders with `id`, `name`, `parent_folder_id`, `depth`.

---

## folder-items
List items inside a folder.

```bash
genviral.sh folder-items --id FOLDER_UUID
genviral.sh folder-items --id FOLDER_UUID --limit 20 --offset 0
genviral.sh folder-items --id FOLDER_UUID --json
```

For `upload`/`ai_image`/`ai_video` folders: returns file objects with URL, content_type, size.
For `slideshow` folders: returns slideshow objects.

---

## folder-items-add
Add files or slideshows to a folder.

```bash
genviral.sh folder-items-add --id FOLDER_UUID --item-ids "UUID1,UUID2,UUID3"
```

Item type must match folder `media_type`:
- `slideshow` folder → pass slideshow IDs
- `upload`/`ai_image`/`ai_video` folder → pass file IDs

Errors:
- `404 item_not_found` — one or more item IDs not visible in scope

---

## folder-items-remove
Remove items from a folder (does not delete the underlying files/slideshows).

```bash
genviral.sh folder-items-remove --id FOLDER_UUID --item-ids "UUID1,UUID2"
```

---

## Typical Workflow

```bash
# 1. Create a folder hierarchy
genviral.sh create-folder --name "Buildfound Ads" --media-type upload
# → returns folder ID, e.g. "abc-123"

genviral.sh create-folder --name "March 2026" --media-type upload --parent-folder-id abc-123
# → returns subfolder ID, e.g. "def-456"

# 2. Upload files and add them to the folder
genviral.sh upload --file ad-slide-1.jpg --content-type image/jpeg
# → returns file ID, e.g. "file-789"

genviral.sh folder-items-add --id def-456 --item-ids "file-789"

# 3. Browse the structure
genviral.sh list-folders --media-type upload
genviral.sh folder-items --id def-456

# 4. Check breadcrumbs
genviral.sh folder-ancestors --id def-456
```
