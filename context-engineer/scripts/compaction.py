"""
Context Compaction and Masking

This module provides utilities for compacting context, managing budgets,
and safely masking observations.
"""

from typing import List, Dict, Optional, Any
import json


# Token Estimation

def estimate_token_count(text: str) -> int:
    """
    Estimate token count for text.
    
    Uses approximation: ~4 characters per token for English.
    
    WARNING: This is an estimation. Production systems must use
    the actual tokenizer for the model being used.
    """
    if not text:
        return 0
    return len(text) // 4


# Context Compaction

def categorize_messages(
    messages: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize messages by role/type."""
    categorized = {
        "system": [],
        "user": [],
        "assistant": [],
        "tool_call": [],
        "tool_output": []
    }
    
    for msg in messages:
        role = msg.get("role")
        if role in categorized:
            categorized[role].append(msg)
        elif role == "tool":
            categorized["tool_output"].append(msg)
    
    return categorized


def compact_history(
    messages: List[Dict[str, Any]], 
    max_tokens: int = 8000
) -> List[Dict[str, Any]]:
    """
    Compact message history to fit within token budget.
    
    Strategy:
    1. Keep system prompt (critical)
    2. Keep last N messages (recency bias)
    3. Summarize older tool outputs
    4. Remove oldest middle messages if still over budget
    """
    if not messages:
        return []
        
    current_tokens = sum(estimate_token_count(m.get("content", "")) for m in messages)
    
    if current_tokens <= max_tokens:
        return messages
    
    compacted = list(messages)
    
    # 1. Compress tool outputs older than last 5 turns
    # Find tool outputs from index 1 (skip system) to -10 (keep last 10)
    for i in range(1, len(compacted) - 10):
        msg = compacted[i]
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            if len(content) > 200:
                compacted[i]["content"] = (
                    f"[Tool output summarized: {len(content)} chars] "
                    f"{content[:50]}...{content[-50:]}"
                )
    
    # Recalculate
    current_tokens = sum(estimate_token_count(m.get("content", "")) for m in compacted)
    if current_tokens <= max_tokens:
        return compacted
        
    # 2. Remove oldest middle messages (keep system + last 10)
    # This is a simple implementation of "lost in middle" mitigation
    # by removing the middle entirely
    
    # Keep system prompt
    system_msg = compacted[0] if compacted[0]["role"] == "system" else None
    start_idx = 1 if system_msg else 0
    
    # Keep last N messages
    last_n = 10
    recent_msgs = compacted[-last_n:]
    
    # Available budget for middle
    budget_remaining = max_tokens - estimate_token_count(system_msg["content"] if system_msg else "") - sum(estimate_token_count(m["content"]) for m in recent_msgs)
    
    middle_msgs = []
    middle_candidates = compacted[start_idx:-last_n]
    
    # Add middle messages until budget filled (most recent first)
    for msg in reversed(middle_candidates):
        tokens = estimate_token_count(msg.get("content", ""))
        if budget_remaining >= tokens:
            middle_msgs.insert(0, msg)
            budget_remaining -= tokens
        else:
            break
            
    resulting_messages = []
    if system_msg:
        resulting_messages.append(system_msg)
    resulting_messages.extend(middle_msgs)
    
    # Add placeholder if messages were removed
    if len(middle_msgs) < len(middle_candidates):
        num_removed = len(middle_candidates) - len(middle_msgs)
        resulting_messages.append({
            "role": "system",
            "content": f"[{num_removed} older messages removed for compaction]"
        })
        
    resulting_messages.extend(recent_msgs)
    
    return resulting_messages


# Observation Masking

class ScratchpadManager:
    """Manage observation masking via scratchpad."""
    
    def __init__(self, scratchpad_dir: str = "/scratchpad"):
        self.scratchpad_dir = scratchpad_dir
        self.masked_obs: Dict[str, str] = {}
        
    def mask_observation(self, content: str, obs_id: str) -> str:
        """
        Mask a large observation, defining a pointer.
        
        Returns the pointer string to inject into context.
        """
        self.masked_obs[obs_id] = content
        
        summary = content[:100].replace("\n", " ")
        lines = content.count("\n") + 1
        size_kb = len(content) / 1024
        
        return (
            f"[Observation masked to save tokens]\n"
            f"ID: {obs_id}\n"
            f"Size: {size_kb:.2f} KB, {lines} lines\n"
            f"Preview: {summary}...\n"
            f"To read full content, use tool: read_scratchpad(id='{obs_id}')"
        )
        
    def get_observation(self, obs_id: str) -> Optional[str]:
        """Retrieve full observation content."""
        return self.masked_obs.get(obs_id)


# KV Cache Optimization

def stabilize_system_prompt(prompt: str) -> str:
    """
    Ensure system prompt is stable for KV cache reuse.
    
    - Moves dynamic content (timestamps, usernames) to user message
    - Standardizes formatting
    """
    # Remove timestamps if present at start
    lines = prompt.split("\n")
    stable_lines = []
    
    dynamic_content = []
    
    for line in lines:
        if "Current Time:" in line or "User:" in line:
            dynamic_content.append(line)
        else:
            stable_lines.append(line)
            
    stable_prompt = "\n".join(stable_lines)
    
    return stable_prompt, "\n".join(dynamic_content)


class BudgetManager:
    """Track and manage token budget across a session."""
    
    def __init__(self, total_budget: int = 100000):
        self.total_budget = total_budget
        self.used_tokens = 0
        self.history: List[int] = []
        
    def record_usage(self, tokens: int):
        """Record token usage for a turn."""
        self.used_tokens += tokens
        self.history.append(tokens)
        
    def get_remaining(self) -> int:
        """Get remaining budget."""
        return max(0, self.total_budget - self.used_tokens)
        
    def should_summarize(self, threshold: float = 0.8) -> bool:
        """Check if summary is needed based on budget usage."""
        return (self.used_tokens / self.total_budget) > threshold
