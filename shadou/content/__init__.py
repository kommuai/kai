"""Workspace content loaders: prompts, FAQ, user-facing copy."""

from shadou.content.copy import ChatCopy, get_chat_copy
from shadou.content.faq import invalidate_faq_cache, load_master_faq_text, master_faq_system_block

# Do not import shadou.content.prompts here — it pulls agent_context and creates a
# circular import when FAQ loads during eval/training (faq -> __init__ -> prompts -> agent_context).

__all__ = [
    "ChatCopy",
    "get_chat_copy",
    "invalidate_faq_cache",
    "load_master_faq_text",
    "master_faq_system_block",
]
