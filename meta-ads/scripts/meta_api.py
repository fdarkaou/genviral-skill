#!/usr/bin/env python3
"""
Meta Ads API Core Library
Wraps the Meta Marketing API (Graph API v21.0) for use in OpenClaw skills.
All calls use a long-lived System User access token stored in config.

Usage:
    from meta_api import MetaAPI
    api = MetaAPI(access_token="...", ad_account_id="act_123456789")
    campaigns = api.get_campaigns()
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone

API_BASE = "https://graph.facebook.com/v21.0"

# Meta returns action types with various prefixes — map short config names to all known variants
ACTION_TYPE_ALIASES = {
    "purchase": {"purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"},
    "lead": {"lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead"},
    "start_trial": {"start_trial", "omni_start_trial", "offsite_conversion.fb_pixel_start_trial"},
    "complete_registration": {
        "complete_registration",
        "omni_complete_registration",
        "offsite_conversion.fb_pixel_complete_registration",
    },
    "subscribe": {"subscribe", "offsite_conversion.fb_pixel_subscribe"},
}

# All Meta rate-limit error codes (retry-worthy)
RATE_LIMIT_CODES = {4, 17, 32, 613, 80000, 80003}


class MetaAPIError(Exception):
    def __init__(self, message, code=None, error_data=None):
        self.code = code
        self.error_data = error_data
        super().__init__(message)


class MetaAPI:
    def __init__(self, access_token: str, ad_account_id: str):
        """
        access_token: Long-lived System User token from Meta Business Manager
        ad_account_id: Format 'act_XXXXXXXXX'
        """
        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"
        self.token = access_token
        self.account_id = ad_account_id

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────

    @staticmethod
    def _action_matches(api_action_type: str, target_action_type: str) -> bool:
        """Check if a Meta API action_type matches the configured target, accounting for prefixed variants."""
        if not api_action_type or not target_action_type:
            return False
        if api_action_type == target_action_type:
            return True
        # Check suffix match (e.g. offsite_conversion.fb_pixel_purchase matches purchase)
        if api_action_type.endswith(f".{target_action_type}"):
            return True
        return api_action_type in ACTION_TYPE_ALIASES.get(target_action_type, set())

    @staticmethod
    def _to_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_int(value, default=0):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    # ─────────────────────────────────────────────
    # HTTP
    # ─────────────────────────────────────────────

    def _request(self, method: str, path: str, params: dict = None, data: dict = None) -> dict:
        """Make a Meta Graph API request with error handling and rate-limit backoff."""
        params = dict(params or {})
        method = method.upper()

        url = f"{API_BASE}/{path.lstrip('/')}"
        auth_headers = {"Authorization": f"Bearer {self.token}"}

        for attempt in range(3):
            try:
                if method == "GET":
                    qs = urllib.parse.urlencode(params, doseq=True)
                    req_url = f"{url}?{qs}" if qs else url
                    req = urllib.request.Request(req_url, headers=auth_headers)
                else:
                    body = urllib.parse.urlencode({**params, **(data or {})}, doseq=True).encode()
                    req = urllib.request.Request(url, data=body, method=method, headers=auth_headers)
                    req.add_header("Content-Type", "application/x-www-form-urlencoded")

                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read())

            except urllib.error.HTTPError as e:
                raw = e.read()
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    payload = {"error": {"message": raw.decode("utf-8", errors="replace") or str(e), "code": e.code}}

                err = payload.get("error", {})
                code = err.get("code")
                msg = err.get("message", str(e))

                # Rate limit — retry with backoff
                if code in RATE_LIMIT_CODES and attempt < 2:
                    wait = 60 * (attempt + 1)
                    print(f"[meta-api] Rate limit hit (code {code}), waiting {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                    continue

                raise MetaAPIError(msg, code=code, error_data=err) from e

            except urllib.error.URLError as e:
                if attempt < 2:
                    time.sleep(5)
                    continue
                raise MetaAPIError(f"Network error: {e}") from e

        raise MetaAPIError("Max retries exceeded")

    def _paginate(self, path: str, params: dict) -> list:
        """Follow Meta pagination (cursors) and collect all results."""
        results = []
        current_params = dict(params)
        current_path = path

        while True:
            resp = self._request("GET", current_path, params=current_params)
            data = resp.get("data", [])
            results.extend(data)

            paging = resp.get("paging", {})
            next_url = paging.get("next")

            if not next_url:
                break

            # Parse next URL back to path + params (version-agnostic)
            parsed = urllib.parse.urlparse(next_url)
            current_path = re.sub(r"^/v\d+\.\d+/", "", parsed.path).lstrip("/")
            qs = urllib.parse.parse_qs(parsed.query)
            # Flatten single-value lists
            current_params = {k: v[0] if len(v) == 1 else v for k, v in qs.items()}
            # Remove access_token from params (Bearer header handles auth)
            current_params.pop("access_token", None)

        return results

    # ─────────────────────────────────────────────
    # CAMPAIGNS
    # ─────────────────────────────────────────────

    def get_campaigns(self, status_filter=None) -> list:
        """List campaigns in this ad account."""
        params = {
            "fields": "id,name,status,objective,daily_budget,lifetime_budget,budget_remaining",
            "limit": 100,
        }
        if status_filter:
            if isinstance(status_filter, str):
                status_filter = [status_filter]
            params["effective_status"] = json.dumps(status_filter)
        return self._paginate(f"{self.account_id}/campaigns", params)

    # ─────────────────────────────────────────────
    # AD SETS
    # ─────────────────────────────────────────────

    def get_adsets(self, campaign_id: str = None, status_filter=None) -> list:
        """List ad sets, optionally filtered by campaign."""
        path = f"{self.account_id}/adsets" if not campaign_id else f"{campaign_id}/adsets"
        params = {
            "fields": "id,name,status,campaign_id,daily_budget,lifetime_budget,bid_amount,optimization_goal",
            "limit": 100,
        }
        if status_filter:
            if isinstance(status_filter, str):
                status_filter = [status_filter]
            params["effective_status"] = json.dumps(status_filter)
        return self._paginate(path, params)

    def pause_adset(self, adset_id: str) -> dict:
        """Pause an ad set."""
        return self._request("POST", adset_id, data={"status": "PAUSED"})

    def resume_adset(self, adset_id: str) -> dict:
        """Activate an ad set."""
        return self._request("POST", adset_id, data={"status": "ACTIVE"})

    def update_adset_budget(self, adset_id: str, daily_budget_cents: int) -> dict:
        """Update daily budget. Budget is in cents (e.g., $50 = 5000)."""
        return self._request("POST", adset_id, data={"daily_budget": str(daily_budget_cents)})

    def pause_campaign(self, campaign_id: str) -> dict:
        return self._request("POST", campaign_id, data={"status": "PAUSED"})

    def resume_campaign(self, campaign_id: str) -> dict:
        return self._request("POST", campaign_id, data={"status": "ACTIVE"})

    # ─────────────────────────────────────────────
    # ADS
    # ─────────────────────────────────────────────

    def get_ads(self, adset_id: str = None) -> list:
        """List ads."""
        path = f"{self.account_id}/ads" if not adset_id else f"{adset_id}/ads"
        params = {
            "fields": "id,name,status,adset_id,campaign_id,creative{id,name,body,title,image_url,video_id,call_to_action_type}",
            "limit": 100,
        }
        return self._paginate(path, params)

    def pause_ad(self, ad_id: str) -> dict:
        return self._request("POST", ad_id, data={"status": "PAUSED"})

    # ─────────────────────────────────────────────
    # INSIGHTS
    # ─────────────────────────────────────────────

    def get_insights(
        self,
        level: str = "campaign",  # campaign | adset | ad
        date_preset: str = None,  # last_3d | last_7d | last_14d | last_28d | last_30d | last_90d
        date_start: str = None,
        date_stop: str = None,
        action_type: str = "purchase",  # purchase | lead | complete_registration
        extra_fields: list = None,
    ) -> list:
        """
        Pull performance insights.
        Returns list of dicts with: spend, impressions, frequency, ctr,
        cost_per_action_type (filtered to action_type), actions.

        Use date_start + date_stop for arbitrary ranges.
        Use date_preset for standard Meta presets (last_3d, last_7d, last_14d, last_28d, last_30d, last_90d).
        """
        fields = [
            "campaign_id", "campaign_name",
            "adset_id", "adset_name",
            "ad_id", "ad_name",
            "spend", "impressions", "reach", "frequency",
            "clicks", "ctr", "cpc", "cpm",
            "cost_per_action_type",
            "actions",
            "purchase_roas",
        ]
        if extra_fields:
            fields.extend(extra_fields)

        params = {
            "fields": ",".join(fields),
            "level": level,
            "limit": 100,
            "action_attribution_windows": '["7d_click","1d_view"]',
        }

        if date_start and date_stop:
            params["time_range"] = json.dumps({"since": date_start, "until": date_stop})
        elif date_preset:
            params["date_preset"] = date_preset
        else:
            params["date_preset"] = "last_7d"  # safe default

        raw = self._paginate(f"{self.account_id}/insights", params)

        # Flatten cost_per_action_type for the target action
        for row in raw:
            cpa_list = row.get("cost_per_action_type", [])
            row["target_cpa"] = None
            for item in cpa_list:
                if self._action_matches(item.get("action_type"), action_type):
                    row["target_cpa"] = self._to_float(item.get("value"), None)
                    break

            # Also extract action count
            actions_list = row.get("actions", [])
            row["target_action_count"] = 0
            for item in actions_list:
                if self._action_matches(item.get("action_type"), action_type):
                    row["target_action_count"] = self._to_int(item.get("value"), 0)
                    break

            # Normalize types (safe against None/malformed values)
            row["spend"] = self._to_float(row.get("spend"), 0.0)
            row["frequency"] = self._to_float(row.get("frequency"), 0.0)
            row["impressions"] = self._to_int(row.get("impressions"), 0)
            row["ctr"] = self._to_float(row.get("ctr"), 0.0)

        return raw

    # ─────────────────────────────────────────────
    # AD CREATIVES (for upload)
    # ─────────────────────────────────────────────

    # ─────────────────────────────────────────────
    # CAMPAIGN & ADSET CREATION
    # ─────────────────────────────────────────────

    def create_campaign(
        self,
        name: str,
        objective: str = "OUTCOME_SALES",
        status: str = "PAUSED",
        special_ad_categories: list = None,
        daily_budget_cents: int = None,
        bid_strategy: str = None,
    ) -> str:
        """Create a campaign and return its ID."""
        data = {
            "name": name,
            "objective": objective,
            "status": status,
            "special_ad_categories": json.dumps(special_ad_categories or []),
        }
        if daily_budget_cents is not None:
            data["daily_budget"] = str(daily_budget_cents)
        if bid_strategy:
            data["bid_strategy"] = bid_strategy
        resp = self._request("POST", f"{self.account_id}/campaigns", data=data)
        return resp["id"]

    def create_adset(
        self,
        name: str,
        campaign_id: str,
        daily_budget_cents: int = None,
        optimization_goal: str = "OFFSITE_CONVERSIONS",
        billing_event: str = "IMPRESSIONS",
        bid_strategy: str = "LOWEST_COST_WITHOUT_CAP",
        targeting: dict = None,
        promoted_object: dict = None,
        status: str = "PAUSED",
        start_time: str = None,
    ) -> str:
        """Create an ad set and return its ID."""
        data = {
            "name": name,
            "campaign_id": campaign_id,
            "optimization_goal": optimization_goal,
            "billing_event": billing_event,
            "bid_strategy": bid_strategy,
            "status": status,
        }
        if daily_budget_cents is not None:
            data["daily_budget"] = str(daily_budget_cents)
        if targeting:
            data["targeting"] = json.dumps(targeting)
        if promoted_object:
            data["promoted_object"] = json.dumps(promoted_object)
        if start_time:
            data["start_time"] = start_time
        resp = self._request("POST", f"{self.account_id}/adsets", data=data)
        return resp["id"]

    # ─────────────────────────────────────────────
    # AD CREATIVE UPLOAD
    # ─────────────────────────────────────────────

    def create_ad_image(self, image_path: str) -> str:
        """Upload an image and return its hash. Uses multipart/form-data for large file support."""
        import uuid

        boundary = uuid.uuid4().hex
        filename = os.path.basename(image_path)

        with open(image_path, "rb") as f:
            file_data = f.read()

        # Build multipart body (no access_token in body — Bearer header handles auth)
        lines = []
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="filename"; filename="{filename}"'.encode())
        lines.append(b"Content-Type: application/octet-stream")
        lines.append(b"")
        lines.append(file_data)
        lines.append(f"--{boundary}--".encode())
        body = b"\r\n".join(lines)

        url = f"{API_BASE}/{self.account_id}/adimages"
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                err_body = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                err_body = {"error": {"message": raw.decode("utf-8", errors="replace") or str(e), "code": e.code}}
            raise MetaAPIError(
                err_body.get("error", {}).get("message", str(e)),
                code=err_body.get("error", {}).get("code"),
            ) from e

        images = result.get("images", {})
        for fname, info in images.items():
            return info["hash"]
        raise MetaAPIError("Image upload returned no hash")

    def create_ad_creative(
        self,
        name: str,
        page_id: str,
        headline: str,
        body: str,
        image_hash: str = None,
        link_url: str = None,
        cta_type: str = "LEARN_MORE",
        description: str = None,
    ) -> str:
        """Create an AdCreative and return its ID."""
        link_data = {
            "message": body,
            "link": link_url or "",
            "name": headline,
            "call_to_action": {"type": cta_type, "value": {"link": link_url or ""}},
        }
        if description:
            link_data["description"] = description
        if image_hash:
            link_data["image_hash"] = image_hash

        creative_spec = {
            "page_id": page_id,
            "link_data": link_data,
        }

        resp = self._request(
            "POST",
            f"{self.account_id}/adcreatives",
            data={
                "name": name,
                "object_story_spec": json.dumps(creative_spec),
            },
        )
        return resp["id"]

    def create_ad(self, name: str, adset_id: str, creative_id: str, status: str = "PAUSED") -> str:
        """Create an ad using an existing creative. Returns ad ID."""
        resp = self._request(
            "POST",
            f"{self.account_id}/ads",
            data={
                "name": name,
                "adset_id": adset_id,
                "creative": json.dumps({"creative_id": creative_id}),
                "status": status,
            },
        )
        return resp["id"]

    # ─────────────────────────────────────────────
    # ACCOUNT INFO
    # ─────────────────────────────────────────────

    def get_account_info(self) -> dict:
        return self._request("GET", self.account_id, params={
            "fields": "id,name,currency,timezone_name,account_status,amount_spent,balance"
        })


def load_config(config_path: str = None) -> dict:
    """Load accounts config from YAML. Returns dict of product configs."""
    import yaml  # standard pyyaml
    path = config_path or os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def cents_to_dollars(cents) -> float:
    return float(cents) / 100.0


def dollars_to_cents(dollars) -> int:
    return int(float(dollars) * 100)
