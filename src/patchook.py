import requests

from patch import Patch, PatchTag
import web_scraper


class Patchook:
    """Class representing the webhook object for posting update patch notes to Discord."""

    def __init__(self, webhook_config: dict, *args, **kwargs) -> None:
        """Initialize Patchook object with webhook configuration."""

        self.original_config = webhook_config
        self.config = webhook_config.copy()

        self._configure_ignore_flags(webhook_config)

        self.available_tags = webhook_config.get("available_tags", None)
        self.url = webhook_config.get("url", None)
        if not self.url:
            raise ValueError("Discord webhook URL is required. Please configure it for each webhook in config.json!")

        self.custom_patch_header = webhook_config.get("custom_patch_header", None)
        self.video_only = webhook_config.get("video_only", False)
        self.forum = webhook_config.get("forum", False)
        self.enabled = webhook_config.get("enabled", True)

        ## Auto-upading fields

        self.info = web_scraper.get_webhook_info(self.url)

        self.guild_id = self.info.get("guild_id", None) if self.info else None
        if self.guild_id: self.config["guild_id"] = self.guild_id

        self.name = self.info.get("name", None) if self.info else None
        if self.name: self.config["name"] = self.name

        self.application_owned = webhook_config.get("application_owned", None)
        if self.application_owned is None and self.info: # This is a constant and never changes without the token.
            self.application_owned = self.info.get("application_owned", False)

        self.last_announced_version = webhook_config.get("last_announced_version", None)
        if self.last_announced_version is None:
            self.last_announced_version = web_scraper.get_newest_version()
            if self.last_announced_version:
                self.config["last_announced_version"] = self.last_announced_version
            else:
                print("Failed to fetch the newest version for Patchook", self.url, "\nPlease update \"last_announced_version\" field in the config JSON file manually.")


    def _configure_ignore_flags(self, webhook_config: dict) -> None:
        """Configure ignore flags based on webhook configuration."""
        ignore_config = webhook_config.get("ignore", {})
        self.ignore_beta = ignore_config.get("beta", False)
        self.ignore_release = ignore_config.get("release", False)
        self.ignore_hotfix = ignore_config.get("hotfix", False)
        self.ignore_major = ignore_config.get("major", False)

    def post(self, patch: Patch) -> requests.Request:
        """Posts the patch notes to the specified Discord webhook.

        Args:
            patch: Patch object to be posted.

        Returns:
            requests.Request object representing the request.
        """
        patch_dict = self._build_patch_dict(patch)
        if not patch_dict:
            return print("[ERROR] Failed to get the patch data!")

        request = self._make_request(patch_dict)
        self._handle_request_response(request)

        return request

    def _build_patch_dict(self, patch: Patch) -> dict:
        """Build patch dictionary for posting to Discord webhook.

        Args:
            patch: Patch object to be posted.

        Returns:
            Dictionary representing the patch to be posted.
        """
        patch_dict = patch.to_dict()
        if self.forum:
            patch_dict["thread_name"] = patch.title

        if self.available_tags is not None:
            patch_dict["applied_tags"] = [int(self.available_tags[tag]) for tag in patch.get_tags() if tag in self.available_tags]

        if self.application_owned:
            patch_dict["components"] = [
                {
                    "type": 1,
                    "components": patch.get_link_buttons()
                }
            ]
        else:
            patch_dict["content"] = patch.get_links_header()

        return self._add_custom_header(patch, patch_dict)

    def _add_custom_header(self, patch: Patch, patch_dict: dict) -> dict:
        """Add custom header to patch dictionary if available.

        Args:
            patch_dict: Dictionary representing the patch to be posted.

        Returns:
            Dictionary representing the patch to be posted with custom header.
        """
        if not self.custom_patch_header:
            return patch_dict # No changes

        patch_tags = patch.get_tags()
        for tags_string, header in self.custom_patch_header.items():
            tags_required, tags_prohibited, tags_optional = [], [], []
            for tag in tags_string.split():
                tag = tag.strip()
                tag_name = tag.strip("!").strip("?")
                if not tag_name in PatchTag.ALL:
                    print("[Warn] Patch tag", tag_name, "is not valid!")
                    continue

                if tag.startswith("!") or tag.endswith("!"):
                    tags_prohibited.append(tag_name)
                elif tag.startswith("?") or tag.endswith("?"):
                    tags_optional.append(tag_name)
                else:
                    tags_required.append(tag_name)

            if (
                all(tag in patch_tags for tag in tags_required) and # All required tags!
                not any(tag in patch_tags for tag in tags_prohibited) and # No prohibited tags!
                all(tag in tags_required or tag in tags_optional for tag in patch_tags) # No redundant tags!
            ):
                patch_dict["content"] = header + \
                    ("\n" + patch_dict["content"] if "content" in patch_dict else "")

        return patch_dict

    def _make_request(self, patch_dict: dict) -> requests.Request:
        """Make request to Discord webhook with patch dictionary.

        Args:
            patch_dict: Dictionary representing the patch to be posted.

        Returns:
            requests.Request object representing the request.
        """
        return requests.post(url=self.url, json=patch_dict, params={"wait": True})

    def _handle_request_response(self, request: requests.Request) -> None:
        """Handle response from Discord webhook request.

        Args:
            request: requests.Request object representing the request.
        """
        if not request.ok:
            print(f"[{request.status_code}]",
                  request.reason, request.text or "")
        else:
            print(f"[{request.status_code}] Successfully posted the patchnotes!")
