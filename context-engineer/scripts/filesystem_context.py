"""
Filesystem Context Patterns

This module implements patterns for filesystem-based context engineering,
including scratchpads, plan persistence, and state tracking.
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime


class ScratchPadManager:
    """
    Manages a scratchpad file for offloading ephemeral thoughts and
    intermediate results from the main context.
    
    Pattern: Context Offloading
    """
    
    def __init__(self, path: str = "scratchpad.md"):
        self.path = path
        self.ensure_exists()
        
    def ensure_exists(self):
        """Create scratchpad if it doesn't exist."""
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                f.write("# Agent Scratchpad\n\nUse this space for temporary notes.\n")
                
    def read(self) -> str:
        """Read scratchpad content."""
        with open(self.path, "r") as f:
            return f.read()
            
    def append(self, content: str):
        """Append note to scratchpad."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"\n\n## Note ({timestamp})\n{content}"
        
        with open(self.path, "a") as f:
            f.write(entry)
            
    def clear(self):
        """Clear scratchpad content."""
        with open(self.path, "w") as f:
            f.write("# Agent Scratchpad\n\n(Cleared)\n")


class AgentPlan:
    """
    Manages a persistent plan file to maintain high-level direction
    across many context windows.
    
    Pattern: Externalized State
    """
    
    def __init__(self, path: str = "plan.md"):
        self.path = path
        self.ensure_exists()
        
    def ensure_exists(self):
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                f.write("# Execution Plan\n\n- [ ] Initialize\n")
                
    def update_task(self, task_id: int, status: str, result: str = ""):
        """
        Update a task status in the plan.
        
        Note: This is a robust parser implementation in production,
        here it uses simple text replacement for demonstration.
        """
        content = self.read()
        lines = content.split("\n")
        
        # Find task line (simplified)
        # In reality, use robust regex or AST
        pass
        
    def read(self) -> str:
        with open(self.path, "r") as f:
            return f.read()


class ContextState:
    """
    Tracks state of the context window (token usage, key entities).
    """
    
    def __init__(self, path: str = ".context_state.json"):
        self.path = path
        self.state = self._load()
        
    def _load(self) -> Dict:
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                return json.load(f)
        return {
            "token_usage_history": [],
            "focus_entities": [],
            "last_summary_hash": ""
        }
        
    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.state, f, indent=2)
            
    def record_usage(self, tokens: int):
        self.state["token_usage_history"].append({
            "timestamp": datetime.now().isoformat(),
            "tokens": tokens
        })
        self.save()


# Tool Functions

def init_workspace(root_dir: str):
    """Initialize filesystem context structures."""
    os.makedirs(root_dir, exist_ok=True)
    
    # Create standard context files
    ScratchPadManager(os.path.join(root_dir, "scratchpad.md"))
    AgentPlan(os.path.join(root_dir, "plan.md"))
    ContextState(os.path.join(root_dir, ".context_state.json"))
    
    return f"Workspace initialized at {root_dir}"

def read_context_files(root_dir: str) -> Dict[str, str]:
    """Read all context-relevant files."""
    files = {
        "scratchpad": ScratchPadManager(os.path.join(root_dir, "scratchpad.md")).read(),
        "plan": AgentPlan(os.path.join(root_dir, "plan.md")).read()
    }
    return files
