import requests

from patch import Patch


class Patchook:
    """Class representing the webhook object for posting update patch notes to Discord."""

    def __init__(self, webhook_config: dict, *args, **kwargs) -> None:
        """Initialize Patchook object with webhook configuration."""

        self._configure_ignore_flags(webhook_config)

        self.available_tags = webhook_config.get("available_tags", None)
        self.url = webhook_config.get("url", None)
        if not self.url:
            raise ValueError("Discord webhook URL is required. Please configure it for each webhook in config.json!")

        self.custom_patch_header = webhook_config.get("custom_patch_header", None)
        self.video_only = webhook_config.get("video_only", False)
        self.forum = webhook_config.get("forum", False)
        self.enabled = webhook_config.get("enabled", True)
        self.application_owned = webhook_config.get("application_owned", False)

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
        patch_dict = patch.to_dict_for()
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

        return self._add_custom_header(patch_dict)

    def _add_custom_header(self, patch_dict: dict) -> dict:
        """Add custom header to patch dictionary if available.

        Args:
            patch_dict: Dictionary representing the patch to be posted.

        Returns:
            Dictionary representing the patch to be posted with custom header.
        """
        if self.custom_patch_header and patch_dict.get("content"):
            patch_dict["content"] = self.custom_patch_header + \
                "\n" + patch_dict["content"]

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
