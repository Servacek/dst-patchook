import requests
import copy

from post import Post, PostTag
from post import Post
from config import config
import web_scraper


class Patchook:
    """Class representing the webhook object for posting update post to Discord."""

    last_announced_version: dict[str, int] = {}

    def __init__(self, webhook_config: dict, *args, **kwargs) -> None:
        """Initialize Patchook object with webhook configuration."""

        self.config = webhook_config

        self.ignore_tag_rule = self.config.get("ignore_tag_rule", None)

        self.available_tags = self.config.get("available_tags", None)
        self.url = self.config.get("url", None)
        if not self.url:
            raise ValueError("Discord webhook URL is required. Please configure it for each webhook in config.json!")

        self.custom_fields = self.config.get("custom_fields", None)
        self.video_only = self.config.get("video_only", False)
        self.forum = self.config.get("forum", False)
        self.enabled = self.config.get("enabled", True)

        ## Auto-upading fields

        self.info = web_scraper.get_webhook_info(self.url)
        self.forum = self.config.get("forum", None)
        if self.forum is None:
            self.channel_id = self.info.get("channel_id", None) if self.info else None
            if self.channel_id:
                self.channel_info = web_scraper.get_channel_info(self.channel_id)
                self.channel_type = self.channel_info.get("type", None) if self.channel_info else None
                self.forum = self.channel_type == 15

        self.guild_id = self.info.get("guild_id", None) if self.info else None
        if self.guild_id: self.config["guild_id"] = self.guild_id

        self.name = self.info.get("name", None) if self.info else None
        if self.name: self.config["name"] = self.name

        self.application_owned = self.config.get("application_owned", None)
        if self.application_owned is None and self.info: # This is a constant and never changes without the token.
            self.application_owned = self.info.get("application_id", None) is not None

        last_announce_version = self.config.get("last_announced_version", {})
        for key in last_announce_version:
            if not isinstance(last_announce_version[key], int):
                # Convert to integer if possible
                if isinstance(last_announce_version[key], str) and last_announce_version[key].isdigit():
                    last_announce_version[key] = int(last_announce_version[key])
                else:
                    del last_announce_version[key]

        if last_announce_version:
            self.last_announced_version = last_announce_version
        else: # Handling the case where no valid "last_announced_version" is saved.
            last_online_version = web_scraper.get_newest_version(Post.DEFAULT_SOURCE_URL)
            last_announce_version[Post.DEFAULT_SOURCE_URL] = last_online_version
            if last_online_version:
                # We have successfully fetched the newest version so we start from here.
                # No updates this run, therefore keep the last_announced_version dictionary empty.
                self.config["last_announced_version"] = self.last_announced_version
            else:
                print("Failed to fetch the newest version for Patchook", self.url, "\nPlease update \"last_announced_version\" field in the config JSON file manually.")

    def can_post(self, post: Post) -> bool:
        return (not (self.ignore_tag_rule and post.meets_tag_rule(self.ignore_tag_rule))) and (
            self.last_announced_version.get(post.source_url, None) is not None and
            (post.version > self.last_announced_version[post.source_url] or config.get('debug_mode', False))
        )

    def post(self, post: Post) -> requests.Response:
        """Sends the post to the specified Discord webhook.

        Args:
            post: Post object to be posted.

        Returns:
            requests.Request object representing the request.
        """
        post_dict = self._build_patch_dict(post)
        if not post_dict:
            return print("[ERROR] Failed to get the post data!")

        # This only works for normal messages since the forum ones are inaccessible for webhooks (the starting thread messages).
        thread_id = None
        message_id = self.config.get("version_to_message_id_map", {}).get(str(post.version), None)
        if message_id:
            message_id = int(message_id) # Ensure this is an integer
        # print(post.version, message_id)
        # if isinstance(message_id, str):
        #     items = message_id.strip().split(">")
        #     print(items)
        #     if len(items) == 2:
        #         thread_id = int(items[0].strip())
        #         message_id = int(items[1].strip())
        #     else:
        #         message_id = int(message_id)

        # if self.forum and message_id is not None:
        #     if thread_id is None:
        #         return print("[Error] No thread ID provided in the 'version_to_message_id_map' for a forum webhook!")

        #     print("Posting to forum!", thread_id, message_id)
        #     patch_dict["thread_id"] = thread_id

        response = self._make_request(post_dict, message_id=message_id)
        self._handle_request_response_for_patch(response, post)

        return response

    def add_buttons(self, post_dict: dict, buttons: list[dict]) -> dict:
        if not post_dict.get("components", None):
            post_dict["components"] = []

        # An Action Row can contain up to 5 buttons.
        # You can have up to 5 Action Rows per message
        buttons_buffer = buttons.copy()
        while (buttons_buffer):
            last_component = post_dict["components"][-1] if post_dict["components"] else None
            if last_component and len(last_component["components"]) < 5:
                last_component["components"].append(buttons_buffer.pop(0)) # Keep the order
                continue

            if len(post_dict["components"]) < 5:
                post_dict["components"].append({"type": 1, "components": []})
                continue

            break

    def _build_patch_dict(self, post: Post) -> dict:
        """Build post dictionary for posting to Discord webhook.

        Args:
            post: Post object to be posted.

        Returns:
            Dictionary representing the post to be posted.
        """
        patch_dict = post.to_dict(config=self.config)
        if self.forum:
            patch_dict["thread_name"] = patch_dict["embeds"][0]["title"]

        if self.available_tags is not None:
            sorted_tags = sorted(post.get_tags())
            patch_dict["applied_tags"] = [int(self.available_tags[tag.id]) for tag in sorted_tags if tag.id in self.available_tags]

        if not (self.config.get("no_links") is True):
            # Only owned applications can display message components.
            if self.application_owned:
                # An Action Row can contain up to 5 buttons.
                # You can have up to 5 Action Rows per message
                self.add_buttons(patch_dict, post.get_link_buttons())
            else:
                patch_dict["content"] = post.get_links_header()

        if config.get("debug_mode", False) is True and self.forum is False:
            patch_dict["content"] = "**TAGS:** " + " ".join("`" + tag.id.upper() + "`" for tag in post.tags) + ("\n" + patch_dict["content"] if "content" in patch_dict else "")

        _dict = self._add_custom_fields(post, patch_dict)
        return _dict

    def _add_custom_fields(self, post: Post, post_dict: dict) -> dict:
        """Add custom header to post dictionary if available.

        Args:
            patch_dict: Dictionary representing the post to be posted.

        Returns:
            Dictionary representing the post to be sent with a custom header.
        """
        if not self.custom_fields:
            return post_dict # No changes

        for tag_rule, fields in self.custom_fields.items():
            if post.meets_tag_rule(tag_rule):
                if "buttons" in fields and fields["buttons"] and "components" in post_dict:
                    self.add_buttons(post_dict, post.get_link_buttons(fields["buttons"]))

                if "content" in fields and fields["content"]:
                    post_dict["content"] = fields["content"] + \
                        ("\n" + post_dict["content"] if "content" in post_dict else "")

        return post_dict

    def _make_request(self, post_dict: dict, message_id: int=None) -> requests.Response:
        """Make request to Discord webhook with post dictionary.

        Args:
            patch_dict: Dictionary representing the post to be posted.
            message_id: Integer representing the message ID to edit. A new message will be created.

        Returns:
            requests.Response object representing the request response.
        """
        # print(patch_dict)
        if message_id is not None:
            return requests.patch(url=self.url + f"/messages/{message_id}", json=post_dict, params={"wait": True})

        return requests.post(url=self.url, json=post_dict, params={"wait": True})

    def _handle_request_response_for_patch(self, response: requests.Response, post: Post) -> None:
        """Handle response from Discord webhook request.

        Args:
            response (requests.Response): Response from Discord webhook request.
            post (Post): Represents the post object receiving this response after being posted.
        """
        if response.ok:
            print(f"[{response.status_code}] Successfully posted the patchnotes!")

            if (post.source_url and post.version):
                self.last_announced_version[post.source_url] = post.version
                self.config["last_announced_version"][post.source_url] = post.version
        else:
            print(f"[{response.status_code}]", response.reason, response.text or "")
