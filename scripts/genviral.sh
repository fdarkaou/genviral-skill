#!/usr/bin/env bash
# ============================================================================
# genviral.sh - Complete Partner API automation (multi-platform)
# ============================================================================
#
# A comprehensive CLI wrapper for genviral's Partner API. Handles accounts,
# file uploads, slideshow generation, rendering, posting (video + slideshow),
# template/pack management, and the full content pipeline for TikTok, Instagram,
# and any supported platform.
#
# Requirements: bash 4+, curl, jq
# Auth: GENVIRAL_API_KEY environment variable (format: public_id.secret)
#
# Usage: genviral.sh <command> [options]
#
# Account & File Commands:
#   accounts            List connected BYO and hosted accounts
#   upload              Upload file to CDN (presigned URL flow)
#   list-files          List uploaded files
#
# Post Commands:
#   create-post         Create a post (video or slideshow, multi-account)
#   update-post         Update an existing post
#   retry-posts         Retry failed/partial posts
#   list-posts          List posts
#   get-post            Get post details
#   delete-posts        Bulk delete posts
#
# Slideshow Commands:
#   generate            Generate a slideshow from prompt or config
#   render              Render a slideshow to images
#   review              Get slideshow details for review
#   update              Update slide text or title
#   regenerate-slide    Regenerate text for one slide
#   duplicate           Clone a slideshow as a new draft
#   delete              Delete a slideshow
#   list-slideshows     List slideshows
#
# Pack Commands:
#   list-packs          List image packs
#   get-pack            Get a single pack with image URLs
#   create-pack         Create a new pack
#   update-pack         Update pack name/visibility
#   delete-pack         Delete a pack
#   add-pack-image      Add an image to a pack
#   delete-pack-image   Remove an image from a pack
#
# Template Commands:
#   list-templates      List slideshow templates
#   get-template        Get a single template
#   create-template     Create a reusable template
#   update-template     Update template fields
#   delete-template     Delete a template
#   create-template-from-slideshow  Convert slideshow to template
#
# Pipeline:
#   post-draft          Post rendered slideshow as draft (legacy TikTok-focused)
#   full-pipeline       End-to-end: generate -> render -> review -> post draft
#
# Other:
#   help                Show this help message
#
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths and Config
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${GENVIRAL_CONFIG:-${SKILL_DIR}/config.yaml}"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Disable colors if NO_COLOR is set or stdout is not a terminal
if [[ -n "${NO_COLOR:-}" ]] || [[ ! -t 1 ]]; then
    RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' DIM='' NC=''
fi

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

error() { echo -e "${RED}Error:${NC} $*" >&2; }
warn()  { echo -e "${YELLOW}Warning:${NC} $*" >&2; }
info()  { echo -e "${BLUE}Info:${NC} $*" >&2; }
ok()    { echo -e "${GREEN}OK:${NC} $*" >&2; }
step()  { echo -e "${CYAN}$*${NC}" >&2; }

die() { error "$@"; exit 1; }

# ---------------------------------------------------------------------------
# Dependency Checks
# ---------------------------------------------------------------------------

check_deps() {
    local missing=()
    for cmd in curl jq; do
        command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        die "Missing required dependencies: ${missing[*]}. Install them and try again."
    fi
}

# ---------------------------------------------------------------------------
# Config Parsing (lightweight YAML, no external parser needed)
# ---------------------------------------------------------------------------

# Read a simple key from the flat YAML config.
# Handles: key: value, key: "value", key: 'value'
config_get() {
    local key="$1"
    local default="${2:-}"

    if [[ ! -f "$CONFIG_FILE" ]]; then
        printf '%s' "$default"
        return
    fi

    local value=""
    value="$(grep -E "^[[:space:]]*${key}:" "$CONFIG_FILE" 2>/dev/null \
        | head -n1 \
        | sed -E 's/^[[:space:]]*[^:]+:[[:space:]]*//' \
        | sed -E 's/[[:space:]]*#.*$//' \
        | sed -E 's/^["'"'"'](.*)["'"'"']$/\1/' \
        || true)"

    # Resolve env var references like ${VAR_NAME}
    if [[ "$value" =~ ^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$ ]]; then
        local var_name="${BASH_REMATCH[1]}"
        value="${!var_name:-}"
    fi

    if [[ -z "$value" || "$value" == "null" ]]; then
        printf '%s' "$default"
    else
        printf '%s' "$value"
    fi
}

# ---------------------------------------------------------------------------
# Load Defaults from Config
# ---------------------------------------------------------------------------

load_defaults() {
    # Load env file if available
    [[ -f "${HOME}/.config/env/global.env" ]] && source "${HOME}/.config/env/global.env" 2>/dev/null || true

    API_KEY="${GENVIRAL_API_KEY:-}"
    BASE_URL="$(config_get base_url "https://www.genviral.io/api/partner/v1")"

    DEFAULT_PACK_ID="$(config_get default_pack_id "")"
    DEFAULT_SLIDE_COUNT="$(config_get default_slide_count "6")"
    DEFAULT_ASPECT_RATIO="$(config_get default_aspect_ratio "9:16")"
    DEFAULT_TYPE="$(config_get default_type "educational")"
    DEFAULT_STYLE="$(config_get default_style_preset "tiktok")"
    DEFAULT_LANGUAGE="$(config_get language "en")"
    DEFAULT_ACCOUNT_IDS="$(config_get default_account_ids "")"
    DEFAULT_PRIVACY="$(config_get privacy_level "PUBLIC_TO_EVERYONE")"
    DEFAULT_POST_MODE="$(config_get post_mode "DIRECT_POST")"

    HTTP_CONNECT_TIMEOUT="$(config_get connect_timeout "10")"
    HTTP_MAX_TIME="$(config_get max_time "120")"
    HTTP_RETRIES="$(config_get retries "2")"
    HTTP_RETRY_DELAY="$(config_get retry_delay "2")"
}

# ---------------------------------------------------------------------------
# Auth Check
# ---------------------------------------------------------------------------

check_auth() {
    if [[ -z "$API_KEY" ]]; then
        die "GENVIRAL_API_KEY is not set.\n  Set it via: export GENVIRAL_API_KEY=\"your_public_id.your_secret\"\n  Or add to ~/.config/env/global.env"
    fi
}

# ---------------------------------------------------------------------------
# API Request Helper
# ---------------------------------------------------------------------------

# Makes an authenticated API request. Returns JSON body on stdout.
# Exits with error on HTTP errors or API errors.
#
# Usage: api_call METHOD /endpoint [JSON_BODY]
api_call() {
    local method="$1"
    local endpoint="$2"
    local body="${3:-}"

    local url="${BASE_URL%/}${endpoint}"

    local curl_args=(
        -sS
        --connect-timeout "$HTTP_CONNECT_TIMEOUT"
        --max-time "$HTTP_MAX_TIME"
        --retry "$HTTP_RETRIES"
        --retry-delay "$HTTP_RETRY_DELAY"
        -X "$method"
        -H "Authorization: Bearer ${API_KEY}"
        -H "Content-Type: application/json"
        -w '\n%{http_code}'
    )

    [[ -n "$body" ]] && curl_args+=(-d "$body")

    local response
    response="$(curl "${curl_args[@]}" "$url" 2>&1)" || {
        die "Request failed: curl error for $method $endpoint"
    }

    local http_code
    http_code="$(printf '%s' "$response" | tail -n1)"
    local response_body
    response_body="$(printf '%s' "$response" | sed '$d')"

    # Check for empty response
    if [[ -z "$response_body" ]]; then
        die "Empty response from API: $method $endpoint (HTTP $http_code)"
    fi

    # Check for valid JSON
    if ! printf '%s' "$response_body" | jq empty >/dev/null 2>&1; then
        die "API returned non-JSON response (HTTP $http_code): ${response_body:0:200}"
    fi

    # Check HTTP status
    if [[ "$http_code" -ge 400 ]]; then
        local msg
        msg="$(printf '%s' "$response_body" | jq -r '.message // .error // .data.message // "Unknown API error"')"
        die "HTTP $http_code: $msg"
    fi

    # Check API-level error
    if printf '%s' "$response_body" | jq -e 'has("ok") and (.ok == false)' >/dev/null 2>&1; then
        local code msg
        code="$(printf '%s' "$response_body" | jq -r '.code // "unknown"')"
        msg="$(printf '%s' "$response_body" | jq -r '.message // "Request failed"')"
        die "API error $code: $msg"
    fi

    printf '%s' "$response_body"
}

# Upload helper for presigned URL flow (raw PUT, no auth header)
upload_to_presigned_url() {
    local presigned_url="$1"
    local file_path="$2"
    local content_type="$3"

    local curl_args=(
        -sS
        --connect-timeout "$HTTP_CONNECT_TIMEOUT"
        --max-time "$HTTP_MAX_TIME"
        --retry "$HTTP_RETRIES"
        --retry-delay "$HTTP_RETRY_DELAY"
        -X PUT
        -H "Content-Type: ${content_type}"
        --data-binary "@${file_path}"
        -w '\n%{http_code}'
    )

    local response
    response="$(curl "${curl_args[@]}" "$presigned_url" 2>&1)" || {
        die "Upload failed: curl error uploading to presigned URL"
    }

    local http_code
    http_code="$(printf '%s' "$response" | tail -n1)"

    if [[ "$http_code" -ge 400 ]]; then
        die "Upload to CDN failed with HTTP $http_code"
    fi
}

# ---------------------------------------------------------------------------
# Validation Helpers
# ---------------------------------------------------------------------------

validate_slide_count() {
    local n="$1"
    [[ "$n" =~ ^[0-9]+$ ]] || die "slide count must be an integer, got: $n"
    (( n >= 1 && n <= 10 )) || die "slide count must be between 1 and 10, got: $n"
}

validate_aspect_ratio() {
    case "$1" in
        9:16|4:5|1:1) ;;
        *) die "aspect ratio must be one of: 9:16, 4:5, 1:1. Got: $1" ;;
    esac
}

validate_type() {
    case "$1" in
        educational|personal) ;;
        *) die "type must be 'educational' or 'personal'. Got: $1" ;;
    esac
}

validate_style() {
    case "$1" in
        tiktok|inverted|shadow|white|black) ;;
        *) die "style must be one of: tiktok, inverted, shadow, white, black. Got: $1" ;;
    esac
}

require_arg() {
    local name="$1"
    local value="$2"
    [[ -n "$value" ]] || die "--$name is required"
}

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

usage() {
    cat <<EOF
${BOLD}genviral.sh${NC} - Complete Partner API automation (multi-platform)

${BOLD}Usage:${NC}
  genviral.sh <command> [options]

${BOLD}Account & File Commands:${NC}
  accounts              List connected BYO and hosted accounts
  upload                Upload file to CDN (presigned URL flow)
  list-files            List uploaded files

${BOLD}Post Commands:${NC}
  create-post           Create a post (video or slideshow, multi-account)
  update-post           Update an existing post
  retry-posts           Retry failed/partial posts
  list-posts            List posts (optionally filter by status)
  get-post              Get details for a specific post
  delete-posts          Bulk delete posts by IDs

${BOLD}Slideshow Commands:${NC}
  generate              Generate a slideshow from prompt or config
  render                Render a slideshow to images
  review                Get slideshow details for review
  update                Update slide text or title
  regenerate-slide      Regenerate text for one slide
  duplicate             Clone a slideshow as a new draft
  delete                Delete a slideshow
  list-slideshows       List slideshows (optionally filter by status)

${BOLD}Pack Commands:${NC}
  list-packs            List available image packs
  get-pack              Get a single pack with image URLs
  create-pack           Create a new pack
  update-pack           Update pack name/visibility
  delete-pack           Delete a pack
  add-pack-image        Add an image to a pack
  delete-pack-image     Remove an image from a pack

${BOLD}Template Commands:${NC}
  list-templates        List slideshow templates
  get-template          Get a single template
  create-template       Create a reusable template
  update-template       Update template fields
  delete-template       Delete a template
  create-template-from-slideshow  Convert slideshow to template

${BOLD}Pipeline (Legacy):${NC}
  post-draft            Post rendered slideshow as draft (TikTok-focused)
  full-pipeline         End-to-end: generate -> render -> review -> post draft

${BOLD}Other:${NC}
  help                  Show this help message

${BOLD}Environment:${NC}
  GENVIRAL_API_KEY      Partner API key (required, format: public_id.secret)
  GENVIRAL_CONFIG       Path to config.yaml (optional, defaults to skill dir)
  NO_COLOR              Disable colored output

${BOLD}Examples:${NC}
  genviral.sh accounts
  genviral.sh upload --file video.mp4 --content-type video/mp4
  genviral.sh create-post --caption "Text" --media-type video --media-url "https://..." --accounts "id1,id2"
  genviral.sh generate --prompt "My roommate said..." --pack-id abc123
  genviral.sh render --id SLIDESHOW_ID
  genviral.sh create-post --caption "Caption" --media-type slideshow --media-urls "url1,url2,url3" --accounts "id1"
EOF
}

# ===========================================================================
# Commands
# ===========================================================================

# ---------------------------------------------------------------------------
# accounts
# ---------------------------------------------------------------------------
cmd_accounts() {
    local json_output=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --json) json_output=true; shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    info "Fetching connected accounts..."

    local response
    response="$(api_call GET /accounts)"

    if [[ "$json_output" == true ]]; then
        printf '%s' "$response" | jq '.data // {}'
        return
    fi

    local count
    count="$(printf '%s' "$response" | jq '.data.accounts | length // 0')"
    ok "Found $count accounts"
    echo ""

    printf '%s' "$response" | jq -r '
        .data.accounts // [] | .[] |
        "  \(.id)\n    Platform: \(.platform)\n    Type: \(.type)\n    Username: @\(.username)\n    Display: \(.display_name)\n    Status: \(.status)\n"
    '
}

# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------
cmd_upload() {
    local file_path=""
    local content_type=""
    local filename=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --file)         file_path="$2"; shift 2 ;;
            --content-type) content_type="$2"; shift 2 ;;
            --filename)     filename="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "file" "$file_path"
    require_arg "content-type" "$content_type"

    [[ -f "$file_path" ]] || die "File not found: $file_path"

    [[ -z "$filename" ]] && filename="$(basename "$file_path")"

    info "Requesting upload URL..."

    local payload
    payload="$(jq -n \
        --arg content_type "$content_type" \
        --arg filename "$filename" \
        '{contentType: $content_type, filename: $filename}'
    )"

    local response
    response="$(api_call POST /files "$payload")"

    local upload_url cdn_url
    upload_url="$(printf '%s' "$response" | jq -r '.data.uploadUrl // empty')"
    cdn_url="$(printf '%s' "$response" | jq -r '.data.url // empty')"

    if [[ -z "$upload_url" || -z "$cdn_url" ]]; then
        die "API did not return uploadUrl or url"
    fi

    step "  Upload URL: ${upload_url:0:60}..."
    step "  CDN URL: $cdn_url"

    info "Uploading file to CDN..."

    upload_to_presigned_url "$upload_url" "$file_path" "$content_type"

    ok "Upload complete!"
    echo ""
    echo "  CDN URL: $cdn_url"
    echo ""

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# list-files
# ---------------------------------------------------------------------------
cmd_list_files() {
    local limit=50
    local offset=0
    local type=""
    local context=""
    local json_output=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --limit)   limit="$2"; shift 2 ;;
            --offset)  offset="$2"; shift 2 ;;
            --type)    type="$2"; shift 2 ;;
            --context) context="$2"; shift 2 ;;
            --json)    json_output=true; shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    local endpoint="/files?limit=${limit}&offset=${offset}"
    [[ -n "$type" ]] && endpoint="${endpoint}&type=${type}"
    [[ -n "$context" ]] && endpoint="${endpoint}&context=${context}"

    info "Fetching files..."

    local response
    response="$(api_call GET "$endpoint")"

    if [[ "$json_output" == true ]]; then
        printf '%s' "$response" | jq '.data // {}'
        return
    fi

    local total
    total="$(printf '%s' "$response" | jq '.data.total // 0')"
    ok "Found $total files (showing ${limit} from offset ${offset})"
    echo ""

    printf '%s' "$response" | jq -r '
        .data.files // [] | .[] |
        "  \(.filename // "unnamed")\n    URL: \(.url)\n    Type: \(.contentType)\n    Size: \(.size) bytes\n    Created: \(.createdAt)\n"
    '
}

# ---------------------------------------------------------------------------
# create-post
# ---------------------------------------------------------------------------
cmd_create_post() {
    local caption=""
    local media_type=""
    local media_url=""
    local media_urls=""
    local music_url=""
    local accounts=""
    local scheduled_at=""
    local external_id=""
    local tiktok_title=""
    local tiktok_description=""
    local tiktok_post_mode=""
    local tiktok_privacy=""
    local tiktok_disable_comment=""
    local tiktok_disable_duet=""
    local tiktok_disable_stitch=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --caption)              caption="$2"; shift 2 ;;
            --media-type)           media_type="$2"; shift 2 ;;
            --media-url)            media_url="$2"; shift 2 ;;
            --media-urls)           media_urls="$2"; shift 2 ;;
            --music-url)            music_url="$2"; shift 2 ;;
            --accounts)             accounts="$2"; shift 2 ;;
            --scheduled-at)         scheduled_at="$2"; shift 2 ;;
            --external-id)          external_id="$2"; shift 2 ;;
            --tiktok-title)         tiktok_title="$2"; shift 2 ;;
            --tiktok-description)   tiktok_description="$2"; shift 2 ;;
            --tiktok-post-mode)     tiktok_post_mode="$2"; shift 2 ;;
            --tiktok-privacy)       tiktok_privacy="$2"; shift 2 ;;
            --tiktok-disable-comment) tiktok_disable_comment="true"; shift ;;
            --tiktok-disable-duet)    tiktok_disable_duet="true"; shift ;;
            --tiktok-disable-stitch)  tiktok_disable_stitch="true"; shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "caption" "$caption"
    require_arg "media-type" "$media_type"
    require_arg "accounts" "$accounts"

    # Validate media type
    case "$media_type" in
        video|slideshow) ;;
        *) die "media-type must be 'video' or 'slideshow', got: $media_type" ;;
    esac

    # Build media object
    local media_obj=""
    if [[ "$media_type" == "video" ]]; then
        require_arg "media-url" "$media_url"
        media_obj="$(jq -n --arg type "$media_type" --arg url "$media_url" '{type: $type, url: $url}')"
    else
        require_arg "media-urls" "$media_urls"
        local urls_array
        urls_array="$(echo "$media_urls" | tr ',' '\n' | jq -R . | jq -sc .)"
        media_obj="$(jq -n --arg type "$media_type" --argjson urls "$urls_array" '{type: $type, urls: $urls}')"
    fi

    # Build accounts array
    local accounts_array
    accounts_array="$(echo "$accounts" | tr ',' '\n' | jq -R . | jq -s 'map({id: .})')"

    # Build payload
    local payload
    payload="$(jq -n \
        --arg caption "$caption" \
        --argjson media "$media_obj" \
        --argjson accounts "$accounts_array" \
        '{caption: $caption, media: $media, accounts: $accounts}'
    )"

    # Add optional fields
    [[ -n "$music_url" ]] && payload="$(printf '%s' "$payload" | jq --arg url "$music_url" '. + {music_url: $url}')"
    [[ -n "$scheduled_at" ]] && payload="$(printf '%s' "$payload" | jq --arg ts "$scheduled_at" '. + {scheduled_at: $ts}')"
    [[ -n "$external_id" ]] && payload="$(printf '%s' "$payload" | jq --arg id "$external_id" '. + {external_id: $id}')"

    # Build TikTok settings if any provided
    if [[ -n "$tiktok_title" || -n "$tiktok_description" || -n "$tiktok_post_mode" || -n "$tiktok_privacy" || -n "$tiktok_disable_comment" || -n "$tiktok_disable_duet" || -n "$tiktok_disable_stitch" ]]; then
        local tiktok_obj='{}'
        [[ -n "$tiktok_title" ]] && tiktok_obj="$(printf '%s' "$tiktok_obj" | jq --arg t "$tiktok_title" '. + {title: $t}')"
        [[ -n "$tiktok_description" ]] && tiktok_obj="$(printf '%s' "$tiktok_obj" | jq --arg d "$tiktok_description" '. + {description: $d}')"
        [[ -n "$tiktok_post_mode" ]] && tiktok_obj="$(printf '%s' "$tiktok_obj" | jq --arg m "$tiktok_post_mode" '. + {post_mode: $m}')"
        [[ -n "$tiktok_privacy" ]] && tiktok_obj="$(printf '%s' "$tiktok_obj" | jq --arg p "$tiktok_privacy" '. + {privacy_level: $p}')"
        [[ -n "$tiktok_disable_comment" ]] && tiktok_obj="$(printf '%s' "$tiktok_obj" | jq '. + {disable_comment: true}')"
        [[ -n "$tiktok_disable_duet" ]] && tiktok_obj="$(printf '%s' "$tiktok_obj" | jq '. + {disable_duet: true}')"
        [[ -n "$tiktok_disable_stitch" ]] && tiktok_obj="$(printf '%s' "$tiktok_obj" | jq '. + {disable_stitch: true}')"
        payload="$(printf '%s' "$payload" | jq --argjson tt "$tiktok_obj" '. + {tiktok: $tt}')"
    fi

    info "Creating post..."
    step "  Caption: ${caption:0:80}$([ ${#caption} -gt 80 ] && echo '...')"
    step "  Media: $media_type"
    step "  Accounts: $accounts"

    local response
    response="$(api_call POST /posts "$payload")"

    local post_id status
    post_id="$(printf '%s' "$response" | jq -r '.data.id // empty')"
    status="$(printf '%s' "$response" | jq -r '.data.status // empty')"

    if [[ -n "$post_id" ]]; then
        ok "Post created: $post_id (status: $status)"
    fi

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# update-post
# ---------------------------------------------------------------------------
cmd_update_post() {
    local post_id=""
    local caption=""
    local media_type=""
    local media_url=""
    local media_urls=""
    local music_url=""
    local accounts=""
    local scheduled_at=""
    local external_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id)           post_id="$2"; shift 2 ;;
            --caption)      caption="$2"; shift 2 ;;
            --media-type)   media_type="$2"; shift 2 ;;
            --media-url)    media_url="$2"; shift 2 ;;
            --media-urls)   media_urls="$2"; shift 2 ;;
            --music-url)    music_url="$2"; shift 2 ;;
            --accounts)     accounts="$2"; shift 2 ;;
            --scheduled-at) scheduled_at="$2"; shift 2 ;;
            --external-id)  external_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$post_id"

    local payload='{}'

    [[ -n "$caption" ]] && payload="$(printf '%s' "$payload" | jq --arg c "$caption" '. + {caption: $c}')"
    [[ -n "$scheduled_at" ]] && payload="$(printf '%s' "$payload" | jq --arg ts "$scheduled_at" '. + {scheduled_at: $ts}')"
    [[ -n "$external_id" ]] && payload="$(printf '%s' "$payload" | jq --arg id "$external_id" '. + {external_id: $id}')"

    # Music URL (null to clear)
    if [[ "$music_url" == "null" ]]; then
        payload="$(printf '%s' "$payload" | jq '. + {music_url: null}')"
    elif [[ -n "$music_url" ]]; then
        payload="$(printf '%s' "$payload" | jq --arg url "$music_url" '. + {music_url: $url}')"
    fi

    # Media update
    if [[ -n "$media_type" ]]; then
        local media_obj=""
        if [[ "$media_type" == "video" ]]; then
            require_arg "media-url" "$media_url"
            media_obj="$(jq -n --arg type "$media_type" --arg url "$media_url" '{type: $type, url: $url}')"
        else
            require_arg "media-urls" "$media_urls"
            local urls_array
            urls_array="$(echo "$media_urls" | tr ',' '\n' | jq -R . | jq -sc .)"
            media_obj="$(jq -n --arg type "$media_type" --argjson urls "$urls_array" '{type: $type, urls: $urls}')"
        fi
        payload="$(printf '%s' "$payload" | jq --argjson media "$media_obj" '. + {media: $media}')"
    fi

    # Accounts update
    if [[ -n "$accounts" ]]; then
        local accounts_array
        accounts_array="$(echo "$accounts" | tr ',' '\n' | jq -R . | jq -s 'map({id: .})')"
        payload="$(printf '%s' "$payload" | jq --argjson accts "$accounts_array" '. + {accounts: $accts}')"
    fi

    # Check for empty payload
    if [[ "$payload" == "{}" ]]; then
        die "No fields provided for update. Use --caption, --media-type, --accounts, --scheduled-at, etc."
    fi

    info "Updating post $post_id..."

    local response
    response="$(api_call PATCH "/posts/${post_id}" "$payload")"

    ok "Post updated."

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# retry-posts
# ---------------------------------------------------------------------------
cmd_retry_posts() {
    local post_ids=""
    local account_ids=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --post-ids)    post_ids="$2"; shift 2 ;;
            --account-ids) account_ids="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "post-ids" "$post_ids"

    local post_ids_array
    post_ids_array="$(echo "$post_ids" | tr ',' '\n' | jq -R . | jq -sc .)"

    local payload
    payload="$(jq -n --argjson ids "$post_ids_array" '{post_ids: $ids}')"

    if [[ -n "$account_ids" ]]; then
        local account_ids_array
        account_ids_array="$(echo "$account_ids" | tr ',' '\n' | jq -R . | jq -sc .)"
        payload="$(printf '%s' "$payload" | jq --argjson accts "$account_ids_array" '. + {account_ids: $accts}')"
    fi

    info "Retrying posts..."

    local response
    response="$(api_call POST /posts/retry "$payload")"

    local retried
    retried="$(printf '%s' "$response" | jq -r '.data.retried // 0')"
    ok "Retried $retried posts"

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# list-packs
# ---------------------------------------------------------------------------
cmd_list_packs() {
    local json_output=false
    local search=""
    local limit=20
    local offset=0
    local include_public=true

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --json)           json_output=true; shift ;;
            --search)         search="$2"; shift 2 ;;
            --limit)          limit="$2"; shift 2 ;;
            --offset)         offset="$2"; shift 2 ;;
            --include-public) include_public="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    local endpoint="/packs?limit=${limit}&offset=${offset}&include_public=${include_public}"
    [[ -n "$search" ]] && endpoint="${endpoint}&search=${search}"

    info "Fetching image packs..."

    local response
    response="$(api_call GET "$endpoint")"

    if [[ "$json_output" == true ]]; then
        printf '%s' "$response" | jq '.data // {}'
        return
    fi

    local count
    count="$(printf '%s' "$response" | jq '.data.packs | length // 0')"
    ok "Found $count packs"
    echo ""

    printf '%s' "$response" | jq -r '
        .data.packs // [] | .[] |
        "  \(.id)\n    Name: \(.name // "unnamed")\n    Images: \(.image_count // 0)\n    Public: \(.is_public)\n"
    '
}

# ---------------------------------------------------------------------------
# get-pack
# ---------------------------------------------------------------------------
cmd_get_pack() {
    local pack_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id) pack_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$pack_id"
    info "Fetching pack $pack_id..."

    local response
    response="$(api_call GET "/packs/${pack_id}")"

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# create-pack
# ---------------------------------------------------------------------------
cmd_create_pack() {
    local name=""
    local is_public=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)      name="$2"; shift 2 ;;
            --is-public) is_public=true; shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "name" "$name"

    local payload
    payload="$(jq -n --arg name "$name" --argjson pub "$is_public" '{name: $name, is_public: $pub}')"

    info "Creating pack..."

    local response
    response="$(api_call POST /packs "$payload")"

    local pack_id
    pack_id="$(printf '%s' "$response" | jq -r '.data.id // empty')"

    if [[ -n "$pack_id" ]]; then
        ok "Pack created: $pack_id"
    fi

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# update-pack
# ---------------------------------------------------------------------------
cmd_update_pack() {
    local pack_id=""
    local name=""
    local is_public=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id)        pack_id="$2"; shift 2 ;;
            --name)      name="$2"; shift 2 ;;
            --is-public) is_public="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$pack_id"

    local payload='{}'
    [[ -n "$name" ]] && payload="$(printf '%s' "$payload" | jq --arg n "$name" '. + {name: $n}')"
    [[ -n "$is_public" ]] && payload="$(printf '%s' "$payload" | jq --argjson pub "$is_public" '. + {is_public: $pub}')"

    if [[ "$payload" == "{}" ]]; then
        die "No fields provided for update. Use --name or --is-public."
    fi

    info "Updating pack $pack_id..."

    local response
    response="$(api_call PATCH "/packs/${pack_id}" "$payload")"

    ok "Pack updated."

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# delete-pack
# ---------------------------------------------------------------------------
cmd_delete_pack() {
    local pack_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id) pack_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$pack_id"
    warn "Deleting pack $pack_id..."

    api_call DELETE "/packs/${pack_id}" >/dev/null

    ok "Pack deleted."
}

# ---------------------------------------------------------------------------
# add-pack-image
# ---------------------------------------------------------------------------
cmd_add_pack_image() {
    local pack_id=""
    local image_url=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --pack-id)   pack_id="$2"; shift 2 ;;
            --image-url) image_url="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "pack-id" "$pack_id"
    require_arg "image-url" "$image_url"

    local payload
    payload="$(jq -n --arg url "$image_url" '{image_url: $url}')"

    info "Adding image to pack $pack_id..."

    local response
    response="$(api_call POST "/packs/${pack_id}/images" "$payload")"

    ok "Image added to pack."

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# delete-pack-image
# ---------------------------------------------------------------------------
cmd_delete_pack_image() {
    local pack_id=""
    local image_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --pack-id)  pack_id="$2"; shift 2 ;;
            --image-id) image_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "pack-id" "$pack_id"
    require_arg "image-id" "$image_id"

    warn "Deleting image $image_id from pack $pack_id..."

    api_call DELETE "/packs/${pack_id}/images/${image_id}" >/dev/null

    ok "Image deleted from pack."
}

# ---------------------------------------------------------------------------
# list-templates
# ---------------------------------------------------------------------------
cmd_list_templates() {
    local search=""
    local limit=20
    local offset=0
    local json_output=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --search) search="$2"; shift 2 ;;
            --limit)  limit="$2"; shift 2 ;;
            --offset) offset="$2"; shift 2 ;;
            --json)   json_output=true; shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    local endpoint="/templates?limit=${limit}&offset=${offset}"
    [[ -n "$search" ]] && endpoint="${endpoint}&search=${search}"

    info "Fetching slideshow templates..."

    local response
    response="$(api_call GET "$endpoint")"

    if [[ "$json_output" == true ]]; then
        printf '%s' "$response" | jq '.data // {}'
        return
    fi

    printf '%s' "$response" | jq '.data // {}'
}

# ---------------------------------------------------------------------------
# get-template
# ---------------------------------------------------------------------------
cmd_get_template() {
    local template_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id) template_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$template_id"
    info "Fetching template $template_id..."

    local response
    response="$(api_call GET "/templates/${template_id}")"

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# create-template
# ---------------------------------------------------------------------------
cmd_create_template() {
    local name=""
    local description=""
    local visibility="private"
    local config_file=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --name)        name="$2"; shift 2 ;;
            --description) description="$2"; shift 2 ;;
            --visibility)  visibility="$2"; shift 2 ;;
            --config-file) config_file="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "name" "$name"
    require_arg "config-file" "$config_file"

    [[ -f "$config_file" ]] || die "Config file not found: $config_file"

    local config
    config="$(cat "$config_file")"

    # Validate JSON
    if ! printf '%s' "$config" | jq empty >/dev/null 2>&1; then
        die "Config file is not valid JSON: $config_file"
    fi

    local payload
    payload="$(jq -n \
        --arg name "$name" \
        --arg visibility "$visibility" \
        --argjson config "$config" \
        '{name: $name, visibility: $visibility, config: $config}'
    )"

    [[ -n "$description" ]] && payload="$(printf '%s' "$payload" | jq --arg d "$description" '. + {description: $d}')"

    info "Creating template..."

    local response
    response="$(api_call POST /templates "$payload")"

    local template_id
    template_id="$(printf '%s' "$response" | jq -r '.data.id // empty')"

    if [[ -n "$template_id" ]]; then
        ok "Template created: $template_id"
    fi

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# update-template
# ---------------------------------------------------------------------------
cmd_update_template() {
    local template_id=""
    local name=""
    local description=""
    local visibility=""
    local config_file=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id)          template_id="$2"; shift 2 ;;
            --name)        name="$2"; shift 2 ;;
            --description) description="$2"; shift 2 ;;
            --visibility)  visibility="$2"; shift 2 ;;
            --config-file) config_file="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$template_id"

    local payload='{}'

    [[ -n "$name" ]] && payload="$(printf '%s' "$payload" | jq --arg n "$name" '. + {name: $n}')"
    [[ -n "$description" ]] && payload="$(printf '%s' "$payload" | jq --arg d "$description" '. + {description: $d}')"
    [[ -n "$visibility" ]] && payload="$(printf '%s' "$payload" | jq --arg v "$visibility" '. + {visibility: $v}')"

    if [[ -n "$config_file" ]]; then
        [[ -f "$config_file" ]] || die "Config file not found: $config_file"
        local config
        config="$(cat "$config_file")"
        if ! printf '%s' "$config" | jq empty >/dev/null 2>&1; then
            die "Config file is not valid JSON: $config_file"
        fi
        payload="$(printf '%s' "$payload" | jq --argjson cfg "$config" '. + {config: $cfg}')"
    fi

    if [[ "$payload" == "{}" ]]; then
        die "No fields provided for update. Use --name, --description, --visibility, or --config-file."
    fi

    info "Updating template $template_id..."

    local response
    response="$(api_call PATCH "/templates/${template_id}" "$payload")"

    ok "Template updated."

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# delete-template
# ---------------------------------------------------------------------------
cmd_delete_template() {
    local template_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id) template_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$template_id"
    warn "Deleting template $template_id..."

    api_call DELETE "/templates/${template_id}" >/dev/null

    ok "Template deleted."
}

# ---------------------------------------------------------------------------
# create-template-from-slideshow
# ---------------------------------------------------------------------------
cmd_create_template_from_slideshow() {
    local slideshow_id=""
    local name=""
    local description=""
    local visibility="private"
    local preserve_text=true

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --slideshow-id)  slideshow_id="$2"; shift 2 ;;
            --name)          name="$2"; shift 2 ;;
            --description)   description="$2"; shift 2 ;;
            --visibility)    visibility="$2"; shift 2 ;;
            --preserve-text) preserve_text="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "slideshow-id" "$slideshow_id"

    local payload
    payload="$(jq -n \
        --arg visibility "$visibility" \
        --argjson preserve "$preserve_text" \
        '{visibility: $visibility, preserve_text: $preserve}'
    )"

    [[ -n "$name" ]] && payload="$(printf '%s' "$payload" | jq --arg n "$name" '. + {name: $n}')"
    [[ -n "$description" ]] && payload="$(printf '%s' "$payload" | jq --arg d "$description" '. + {description: $d}')"

    info "Creating template from slideshow $slideshow_id..."

    local response
    response="$(api_call POST "/templates/from-slideshow/${slideshow_id}" "$payload")"

    local template_id
    template_id="$(printf '%s' "$response" | jq -r '.data.id // empty')"

    if [[ -n "$template_id" ]]; then
        ok "Template created: $template_id"
    fi

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------
cmd_generate() {
    local prompt=""
    local pack_id="$DEFAULT_PACK_ID"
    local slides="$DEFAULT_SLIDE_COUNT"
    local type="$DEFAULT_TYPE"
    local aspect_ratio="$DEFAULT_ASPECT_RATIO"
    local style="$DEFAULT_STYLE"
    local language="$DEFAULT_LANGUAGE"
    local font_size=""
    local text_width=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --prompt)       prompt="$2"; shift 2 ;;
            --pack-id)      pack_id="$2"; shift 2 ;;
            --slides)       slides="$2"; shift 2 ;;
            --type)         type="$2"; shift 2 ;;
            --aspect-ratio) aspect_ratio="$2"; shift 2 ;;
            --style)        style="$2"; shift 2 ;;
            --language)     language="$2"; shift 2 ;;
            --font-size)    font_size="$2"; shift 2 ;;
            --text-width)   text_width="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "prompt" "$prompt"
    require_arg "pack-id" "$pack_id"
    validate_slide_count "$slides"
    validate_aspect_ratio "$aspect_ratio"
    validate_type "$type"
    validate_style "$style"

    info "Generating slideshow..."
    step "  Prompt: ${prompt:0:80}$([ ${#prompt} -gt 80 ] && echo '...')"
    step "  Pack: $pack_id | Slides: $slides | Type: $type | Ratio: $aspect_ratio | Style: $style"

    # Build advanced settings
    local advanced='{}'
    advanced="$(printf '%s' "$advanced" | jq --arg preset "$style" '. + {text_preset: $preset}')"
    [[ -n "$font_size" ]] && advanced="$(printf '%s' "$advanced" | jq --argjson fs "$font_size" '. + {font_size: $fs}')"
    [[ -n "$text_width" ]] && advanced="$(printf '%s' "$advanced" | jq --argjson tw "$text_width" '. + {text_width: $tw}')"

    local payload
    payload="$(jq -n \
        --arg prompt "$prompt" \
        --arg pack_id "$pack_id" \
        --argjson slide_count "$slides" \
        --arg slideshow_type "$type" \
        --arg aspect_ratio "$aspect_ratio" \
        --arg language "$language" \
        --argjson advanced "$advanced" \
        '{
            prompt: $prompt,
            pack_id: $pack_id,
            slide_count: $slide_count,
            slideshow_type: $slideshow_type,
            aspect_ratio: $aspect_ratio,
            language: $language,
            advanced_settings: $advanced
        }'
    )"

    local response
    response="$(api_call POST /slideshows/generate "$payload")"

    local slideshow_id
    slideshow_id="$(printf '%s' "$response" | jq -r '.data.id // .data._id // .data.slideshow.id // empty')"

    if [[ -n "$slideshow_id" ]]; then
        ok "Slideshow generated: $slideshow_id"
    fi

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
cmd_render() {
    local slideshow_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id) slideshow_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$slideshow_id"
    info "Rendering slideshow $slideshow_id (this may take 10-30 seconds)..."

    local response
    response="$(api_call POST "/slideshows/${slideshow_id}/render" "{}")"

    local status
    status="$(printf '%s' "$response" | jq -r '.data.status // .data.slideshow.status // "unknown"')"
    local url_count
    url_count="$(printf '%s' "$response" | jq '[.data.rendered_image_urls // .data.slideshow.rendered_image_urls // [] | .[] | select(. != null and . != "")] | length')"

    ok "Render complete. Status: $status, Images: $url_count"

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------
cmd_review() {
    local slideshow_id=""
    local json_output=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id) slideshow_id="$2"; shift 2 ;;
            --json) json_output=true; shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$slideshow_id"
    info "Fetching slideshow $slideshow_id..."

    local response
    response="$(api_call GET "/slideshows/${slideshow_id}")"

    local data
    data="$(printf '%s' "$response" | jq '.data')"

    if [[ "$json_output" == true ]]; then
        printf '%s' "$data"
        return
    fi

    # Pretty print summary
    local title status slide_count
    title="$(printf '%s' "$data" | jq -r '.title // "untitled"')"
    status="$(printf '%s' "$data" | jq -r '.status // "unknown"')"
    slide_count="$(printf '%s' "$data" | jq '.slides | length // 0')"

    echo "" >&2
    echo -e "${BOLD}Slideshow Review${NC}" >&2
    echo -e "  ID:     $slideshow_id" >&2
    echo -e "  Title:  $title" >&2
    echo -e "  Status: $status" >&2
    echo -e "  Slides: $slide_count" >&2
    echo "" >&2

    # Show each slide's text
    printf '%s' "$data" | jq -r '
        .slides // [] | to_entries[] |
        "  Slide \(.key + 1): \(.value.text // .value.content // "no text")"
    ' >&2

    # Show rendered URLs if available
    local rendered_count
    rendered_count="$(printf '%s' "$data" | jq '[.rendered_image_urls // [] | .[] | select(. != null and . != "")] | length')"
    if [[ "$rendered_count" -gt 0 ]]; then
        echo "" >&2
        echo -e "  ${GREEN}Rendered images ($rendered_count):${NC}" >&2
        printf '%s' "$data" | jq -r '.rendered_image_urls // [] | .[] | "    " + .' >&2
    fi

    echo "" >&2

    # Output JSON for programmatic use
    printf '%s' "$data"
}

# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------
cmd_update() {
    local slideshow_id=""
    local slides_json=""
    local title=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id)     slideshow_id="$2"; shift 2 ;;
            --slides) slides_json="$2"; shift 2 ;;
            --title)  title="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$slideshow_id"

    if [[ -z "$slides_json" && -z "$title" ]]; then
        die "At least one of --slides or --title is required"
    fi

    local body='{}'
    [[ -n "$slides_json" ]] && body="$(printf '%s' "$body" | jq --argjson slides "$slides_json" '. + {slides: $slides}')"
    [[ -n "$title" ]] && body="$(printf '%s' "$body" | jq --arg title "$title" '. + {title: $title}')"

    info "Updating slideshow $slideshow_id..."

    local response
    response="$(api_call PATCH "/slideshows/${slideshow_id}" "$body")"

    ok "Slideshow updated. Re-render to apply visual changes."

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# regenerate-slide
# ---------------------------------------------------------------------------
cmd_regenerate_slide() {
    local slideshow_id=""
    local slide_index=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id)    slideshow_id="$2"; shift 2 ;;
            --index) slide_index="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$slideshow_id"
    require_arg "index" "$slide_index"

    info "Regenerating slide $slide_index for slideshow $slideshow_id..."

    local response
    response="$(api_call POST "/slideshows/${slideshow_id}/slides/${slide_index}/regenerate")"

    ok "Slide $slide_index regenerated."

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# duplicate
# ---------------------------------------------------------------------------
cmd_duplicate() {
    local slideshow_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id) slideshow_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$slideshow_id"
    info "Duplicating slideshow $slideshow_id..."

    local response
    response="$(api_call POST "/slideshows/${slideshow_id}/duplicate")"

    local new_id
    new_id="$(printf '%s' "$response" | jq -r '.data.id // .data._id // empty')"

    if [[ -n "$new_id" ]]; then
        ok "Duplicated as new slideshow: $new_id"
    fi

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------
cmd_delete() {
    local slideshow_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id) slideshow_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$slideshow_id"
    warn "Deleting slideshow $slideshow_id..."

    api_call DELETE "/slideshows/${slideshow_id}" >/dev/null

    ok "Slideshow deleted."
}

# ---------------------------------------------------------------------------
# list-slideshows
# ---------------------------------------------------------------------------
cmd_list_slideshows() {
    local status_filter=""
    local json_output=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --status) status_filter="$2"; shift 2 ;;
            --json) json_output=true; shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    local endpoint="/slideshows"
    [[ -n "$status_filter" ]] && endpoint="${endpoint}?status=${status_filter}"

    info "Fetching slideshows..."

    local response
    response="$(api_call GET "$endpoint")"

    if [[ "$json_output" == true ]]; then
        printf '%s' "$response" | jq '.data // []'
        return
    fi

    local count
    count="$(printf '%s' "$response" | jq '.data | length // 0')"
    ok "Found $count slideshows"

    printf '%s' "$response" | jq '.data // []'
}

# ---------------------------------------------------------------------------
# post-draft (legacy TikTok-focused command)
# ---------------------------------------------------------------------------
cmd_post_draft() {
    local slideshow_id=""
    local caption=""
    local account_ids="$DEFAULT_ACCOUNT_IDS"
    local privacy="$DEFAULT_PRIVACY"
    local post_mode="$DEFAULT_POST_MODE"
    local scheduled_at=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id)           slideshow_id="$2"; shift 2 ;;
            --caption)      caption="$2"; shift 2 ;;
            --account-ids)  account_ids="$2"; shift 2 ;;
            --privacy)      privacy="$2"; shift 2 ;;
            --post-mode)    post_mode="$2"; shift 2 ;;
            --scheduled-at) scheduled_at="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$slideshow_id"
    require_arg "caption" "$caption"

    if [[ -z "$account_ids" ]]; then
        die "--account-ids is required (or set default_account_ids in config.yaml)"
    fi

    # Fetch rendered image URLs from the slideshow
    info "Fetching rendered slideshow for posting..."

    local slideshow_response
    slideshow_response="$(api_call GET "/slideshows/${slideshow_id}")"

    local rendered_urls
    rendered_urls="$(printf '%s' "$slideshow_response" | jq -c '
        [
            (.data.rendered_image_urls // [])[] ,
            ((.data.slides // [])[] | .rendered_image_url // empty)
        ] | map(select(. != null and . != "")) | unique
    ')"

    local url_count
    url_count="$(printf '%s' "$rendered_urls" | jq 'length')"

    if [[ "$url_count" -eq 0 ]]; then
        die "No rendered images found. Run 'render' first."
    fi

    step "  Found $url_count rendered images"

    # Build accounts array
    local accounts_array
    accounts_array="$(echo "$account_ids" | tr ',' '\n' | jq -R . | jq -s 'map({id: .})')"

    # Build post body
    local payload
    payload="$(jq -n \
        --arg caption "$caption" \
        --argjson urls "$rendered_urls" \
        --argjson accounts "$accounts_array" \
        --arg privacy_level "$privacy" \
        --arg post_mode "$post_mode" \
        --arg scheduled_at "$scheduled_at" \
        '{
            caption: $caption,
            media: {
                type: "slideshow",
                urls: $urls
            },
            accounts: $accounts,
            tiktok: {
                privacy_level: $privacy_level,
                post_mode: $post_mode
            }
        }
        + (if $scheduled_at != "" then { scheduled_at: $scheduled_at } else {} end)
    ')"

    info "Posting as draft..."

    local response
    response="$(api_call POST /posts "$payload")"

    local post_id
    post_id="$(printf '%s' "$response" | jq -r '.data.id // .data._id // .data.post.id // empty')"

    if [[ -n "$post_id" ]]; then
        ok "Draft posted: $post_id"
        step "  Caption: ${caption:0:100}$([ ${#caption} -gt 100 ] && echo '...')"
        echo -e "  ${YELLOW}Action needed: Open TikTok, find the draft, add music, and publish.${NC}" >&2
    fi

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# list-posts
# ---------------------------------------------------------------------------
cmd_list_posts() {
    local status_filter=""
    local limit=20
    local since=""
    local until=""
    local json_output=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --status) status_filter="$2"; shift 2 ;;
            --limit)  limit="$2"; shift 2 ;;
            --since)  since="$2"; shift 2 ;;
            --until)  until="$2"; shift 2 ;;
            --json)   json_output=true; shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    local endpoint="/posts?limit=${limit}"
    [[ -n "$status_filter" ]] && endpoint="${endpoint}&status=${status_filter}"
    [[ -n "$since" ]] && endpoint="${endpoint}&since=${since}"
    [[ -n "$until" ]] && endpoint="${endpoint}&until=${until}"

    info "Fetching posts..."

    local response
    response="$(api_call GET "$endpoint")"

    if [[ "$json_output" == true ]]; then
        printf '%s' "$response" | jq '.data // {}'
        return
    fi

    local count
    count="$(printf '%s' "$response" | jq '.data.posts | length // 0')"
    local total
    total="$(printf '%s' "$response" | jq '.data.summary.total // 0')"
    ok "Found $count posts (total: $total)"

    printf '%s' "$response" | jq '.data // {}'
}

# ---------------------------------------------------------------------------
# get-post
# ---------------------------------------------------------------------------
cmd_get_post() {
    local post_id=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --id) post_id="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "id" "$post_id"
    info "Fetching post $post_id..."

    local response
    response="$(api_call GET "/posts/${post_id}")"

    printf '%s' "$response" | jq '.data'
}

# ---------------------------------------------------------------------------
# delete-posts
# ---------------------------------------------------------------------------
cmd_delete_posts() {
    local ids=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --ids) ids="$2"; shift 2 ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "ids" "$ids"

    # Convert comma-separated IDs to JSON array
    local ids_json
    ids_json="$(echo "$ids" | tr ',' '\n' | jq -R . | jq -sc .)"

    warn "Deleting posts..."

    local payload
    payload="$(jq -n --argjson ids "$ids_json" '{ids: $ids}')"

    local response
    response="$(api_call DELETE /posts "$payload")"

    ok "Posts deleted."
}

# ---------------------------------------------------------------------------
# full-pipeline (legacy TikTok-focused command)
# ---------------------------------------------------------------------------
cmd_full_pipeline() {
    local prompt=""
    local caption=""
    local pack_id="$DEFAULT_PACK_ID"
    local slides="$DEFAULT_SLIDE_COUNT"
    local type="$DEFAULT_TYPE"
    local aspect_ratio="$DEFAULT_ASPECT_RATIO"
    local style="$DEFAULT_STYLE"
    local language="$DEFAULT_LANGUAGE"
    local account_ids="$DEFAULT_ACCOUNT_IDS"
    local skip_post=false
    local font_size=""
    local text_width=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --prompt)       prompt="$2"; shift 2 ;;
            --caption)      caption="$2"; shift 2 ;;
            --pack-id)      pack_id="$2"; shift 2 ;;
            --slides)       slides="$2"; shift 2 ;;
            --type)         type="$2"; shift 2 ;;
            --aspect-ratio) aspect_ratio="$2"; shift 2 ;;
            --style)        style="$2"; shift 2 ;;
            --language)     language="$2"; shift 2 ;;
            --account-ids)  account_ids="$2"; shift 2 ;;
            --font-size)    font_size="$2"; shift 2 ;;
            --text-width)   text_width="$2"; shift 2 ;;
            --skip-post)    skip_post=true; shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    require_arg "prompt" "$prompt"

    if [[ "$skip_post" == false && -z "$caption" ]]; then
        die "--caption is required (or use --skip-post to skip posting)"
    fi

    echo "" >&2
    echo -e "${BOLD}=== Full Pipeline ===${NC}" >&2

    # ----- Step 1: Generate -----
    echo "" >&2
    step "Step 1/4: Generate slideshow"

    local gen_args=(--prompt "$prompt" --pack-id "$pack_id" --slides "$slides" --type "$type" --aspect-ratio "$aspect_ratio" --style "$style" --language "$language")
    [[ -n "$font_size" ]] && gen_args+=(--font-size "$font_size")
    [[ -n "$text_width" ]] && gen_args+=(--text-width "$text_width")

    local gen_result
    gen_result="$(cmd_generate "${gen_args[@]}")" || die "Pipeline failed at generation step."

    local slideshow_id
    slideshow_id="$(printf '%s' "$gen_result" | jq -r '.id // ._id // .slideshow.id // empty')"

    if [[ -z "$slideshow_id" ]]; then
        die "Could not extract slideshow ID from generation response."
    fi

    step "  Slideshow ID: $slideshow_id"

    # ----- Step 2: Render -----
    echo "" >&2
    step "Step 2/4: Render slideshow"

    local render_result
    render_result="$(cmd_render --id "$slideshow_id")" || die "Pipeline failed at render step."

    # ----- Step 3: Review -----
    echo "" >&2
    step "Step 3/4: Review rendered slideshow"

    local review_result
    review_result="$(cmd_review --id "$slideshow_id" --json)" || die "Pipeline failed at review step."

    # ----- Step 4: Post -----
    local post_id=""
    if [[ "$skip_post" == true ]]; then
        echo "" >&2
        step "Step 4/4: Skipped (--skip-post)"
    else
        echo "" >&2
        step "Step 4/4: Post as draft"

        local post_result
        post_result="$(cmd_post_draft --id "$slideshow_id" --caption "$caption" --account-ids "$account_ids")" || die "Pipeline failed at post step."

        post_id="$(printf '%s' "$post_result" | jq -r '.id // ._id // .post.id // empty')"
    fi

    # ----- Summary -----
    echo "" >&2
    echo -e "${GREEN}${BOLD}=== Pipeline Complete ===${NC}" >&2
    step "  Slideshow: $slideshow_id"

    # Show rendered URLs
    local urls
    urls="$(printf '%s' "$render_result" | jq -r '.rendered_image_urls // [] | .[]' 2>/dev/null || true)"
    if [[ -n "$urls" ]]; then
        step "  Rendered slides:"
        while IFS= read -r url; do
            step "    $url"
        done <<< "$urls"
    fi

    if [[ "$skip_post" == false && -n "$post_id" ]]; then
        step "  Post: $post_id"
        step "  Caption: ${caption:0:100}$([ ${#caption} -gt 100 ] && echo '...')"
    fi

    echo "" >&2

    # Output structured JSON result
    local output
    if [[ "$skip_post" == true ]]; then
        output="$(jq -n \
            --arg slideshow_id "$slideshow_id" \
            '{
                slideshow_id: $slideshow_id,
                status: "rendered",
                posted: false
            }'
        )"
    else
        output="$(jq -n \
            --arg slideshow_id "$slideshow_id" \
            --arg post_id "${post_id:-unknown}" \
            --arg caption "$caption" \
            '{
                slideshow_id: $slideshow_id,
                post_id: $post_id,
                caption: $caption,
                status: "draft_posted",
                posted: true
            }'
        )"
    fi

    printf '%s' "$output"
}

# ===========================================================================
# Main Entry Point
# ===========================================================================

check_deps
load_defaults

COMMAND="${1:-help}"
shift 2>/dev/null || true

case "$COMMAND" in
    # Account & File Commands
    accounts)                         check_auth; cmd_accounts "$@" ;;
    upload)                           check_auth; cmd_upload "$@" ;;
    list-files)                       check_auth; cmd_list_files "$@" ;;

    # Post Commands
    create-post)                      check_auth; cmd_create_post "$@" ;;
    update-post)                      check_auth; cmd_update_post "$@" ;;
    retry-posts)                      check_auth; cmd_retry_posts "$@" ;;
    list-posts)                       check_auth; cmd_list_posts "$@" ;;
    get-post)                         check_auth; cmd_get_post "$@" ;;
    delete-posts)                     check_auth; cmd_delete_posts "$@" ;;

    # Slideshow Commands
    generate)                         check_auth; cmd_generate "$@" ;;
    render)                           check_auth; cmd_render "$@" ;;
    review)                           check_auth; cmd_review "$@" ;;
    update)                           check_auth; cmd_update "$@" ;;
    regenerate-slide)                 check_auth; cmd_regenerate_slide "$@" ;;
    duplicate)                        check_auth; cmd_duplicate "$@" ;;
    delete)                           check_auth; cmd_delete "$@" ;;
    list-slideshows)                  check_auth; cmd_list_slideshows "$@" ;;

    # Pack Commands
    list-packs)                       check_auth; cmd_list_packs "$@" ;;
    get-pack)                         check_auth; cmd_get_pack "$@" ;;
    create-pack)                      check_auth; cmd_create_pack "$@" ;;
    update-pack)                      check_auth; cmd_update_pack "$@" ;;
    delete-pack)                      check_auth; cmd_delete_pack "$@" ;;
    add-pack-image)                   check_auth; cmd_add_pack_image "$@" ;;
    delete-pack-image)                check_auth; cmd_delete_pack_image "$@" ;;

    # Template Commands
    list-templates)                   check_auth; cmd_list_templates "$@" ;;
    get-template)                     check_auth; cmd_get_template "$@" ;;
    create-template)                  check_auth; cmd_create_template "$@" ;;
    update-template)                  check_auth; cmd_update_template "$@" ;;
    delete-template)                  check_auth; cmd_delete_template "$@" ;;
    create-template-from-slideshow)   check_auth; cmd_create_template_from_slideshow "$@" ;;

    # Legacy Pipeline Commands
    post-draft)                       check_auth; cmd_post_draft "$@" ;;
    full-pipeline)                    check_auth; cmd_full_pipeline "$@" ;;

    # Help
    help|--help|-h)                   usage ;;

    *)
        error "Unknown command: $COMMAND"
        echo "" >&2
        usage >&2
        exit 1
        ;;
esac
