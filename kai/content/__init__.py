"""Workspace content loaders: prompts, FAQ, user-facing copy."""

from kai.content.copy import ChatCopy, get_chat_copy
from kai.content.faq import invalidate_faq_cache, load_master_faq_text, master_faq_system_block
from kai.content.prompts import build_system_prompt, local_clock_block, load_system_prompt_body

__all__ = [
    "ChatCopy",
    "build_system_prompt",
    "get_chat_copy",
    "invalidate_faq_cache",
    "load_master_faq_text",
    "load_system_prompt_body",
    "local_clock_block",
    "master_faq_system_block",
]
