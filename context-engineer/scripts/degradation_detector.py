"""
Context Degradation Detection

This module contains utilities for detecting and measuring context degradation
issues such as "lost-in-middle", attention dilution, and contamination.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import math
import re


@dataclass
class ContextHealthScore:
    """Overall health score for a context window."""
    score: float  # 0.0 to 1.0
    issues: List[str]
    recommendations: List[str]
    details: Dict[str, Any]


class DegradationDetector:
    """Detects signs of context degradation."""
    
    def __init__(self, max_context_tokens: int = 128000):
        self.max_tokens = max_context_tokens
    
    def analyze_context(self, messages: List[Dict[str, Any]]) -> ContextHealthScore:
        """
        Analyze message history for degradation signs.
        
        Checks for:
        1. Context length saturation
        2. Attention dilution (too many distinct topics)
        3. Structural fragmentation
        4. Instruction drift
        """
        issues = []
        recommendations = []
        details = {}
        
        # 1. Length Check
        total_tokens = self._estimate_tokens(messages)
        saturation = total_tokens / self.max_tokens
        details["saturation"] = saturation
        
        if saturation > 0.8:
            issues.append("Context saturation critical (>80%)")
            recommendations.append("Perform immediate compression or summarization")
        elif saturation > 0.6:
            issues.append("Context saturation high (>60%)")
            recommendations.append("Prepare for summarization")
            
        # 2. Structure Check
        structure_score = self._check_structure(messages)
        details["structure_score"] = structure_score
        
        if structure_score < 0.5:
            issues.append("Poor context structure (fragmented)")
            recommendations.append("Consolidate small messages and tool outputs")
            
        # 3. Instruction Drift Check
        drift_score = self._check_instruction_drift(messages)
        details["drift_score"] = drift_score
        
        if drift_score > 0.7:
            issues.append("High instruction drift detected")
            recommendations.append("Reinject system prompt or core instructions")
            
        # Calculate overall score
        # Start at 1.0 and deduct penalties
        score = 1.0
        score -= min(0.5, saturation * 0.5)  # Up to 0.25 penalty for saturation
        score -= (1.0 - structure_score) * 0.2  # Up to 0.2 penalty for structure
        score -= drift_score * 0.3  # Up to 0.3 penalty for drift
        
        return ContextHealthScore(
            score=max(0.0, score),
            issues=issues,
            recommendations=recommendations,
            details=details
        )
    
    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """Estimate token count (approximate)."""
        text = "".join(m.get("content", "") or "" for m in messages)
        return len(text) // 4
    
    def _check_structure(self, messages: List[Dict]) -> float:
        """
        Evaluate structural integrity of context.
        
        Penalizes:
        - Alternating short messages (fragmentation)
        - Broken tool chains (call without output)
        - Orphaned tool outputs
        """
        if not messages:
            return 1.0
            
        score = 1.0
        
        # Check fragmentation
        short_msg_run = 0
        for msg in messages:
            content = msg.get("content", "") or ""
            if len(content) < 50:
                short_msg_run += 1
            else:
                short_msg_run = 0
            
            if short_msg_run > 3:
                score -= 0.05  # Penalty for run of short messages
        
        # Check tool chains
        pending_tool_calls = set()
        for msg in messages:
            role = msg.get("role")
            
            if role == "assistant" and "tool_calls" in msg:
                for tc in msg.get("tool_calls", []):
                    pending_tool_calls.add(tc.get("id"))
            
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id")
                if tool_call_id in pending_tool_calls:
                    pending_tool_calls.remove(tool_call_id)
                else:
                    score -= 0.1  # Orphaned output penalty
        
        if pending_tool_calls:
             score -= 0.1 * len(pending_tool_calls)  # Unanswered call penalty
             
        return max(0.0, score)
    
    def _check_instruction_drift(self, messages: List[Dict]) -> float:
        """
        Estimate instruction drift based on topic shifts.
        
        High score = high drift (bad).
        """
        # Heuristic: distance from last system/instruction message
        last_instruction_idx = -1
        
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                last_instruction_idx = i
                
        if last_instruction_idx == -1:
            return 1.0  # No instructions found!
            
        # Distance penalty
        distance = len(messages) - last_instruction_idx
        drift = min(1.0, distance / 50.0)  # Max drift at 50 messages
        
        return drift


# Attention Distribution Simulation

class AttentionSimulator:
    """
    Simulates how attention might be distributed over context.
    
    Implements a simplified decay + peak model (U-shaped attention).
    """
    
    def __init__(self, size: int):
        self.size = size
        self.distribution = [0.0] * size
        
    def simulate(self) -> List[float]:
        """Generate attention weights for each position."""
        # Simple U-shaped curve approximation
        # High at start (primacy), High at end (recency), Dip in middle
        
        for i in range(self.size):
            # Normalized position 0..1
            pos = i / max(1, self.size - 1)
            
            # Primacy component (decaying from start)
            primacy = math.exp(-pos * 10)
            
            # Recency component (decaying from end)
            recency = math.exp(-(1-pos) * 10)
            
            # Combine
            self.distribution[i] = max(primacy, recency)
            
            # Add "needle" spikes for key terms (simulated)
            # In real system, this would value content relevance
            
        return self.distribution
    
    def get_lost_in_middle_risk(self) -> float:
        """Calculate risk of information loss in middle."""
        mid_start = int(self.size * 0.25)
        mid_end = int(self.size * 0.75)
        
        if mid_end <= mid_start:
            return 0.0
            
        middle_weights = self.distribution[mid_start:mid_end]
        avg_middle = sum(middle_weights) / len(middle_weights)
        
        # Risk is inverse of average middle attention
        return 1.0 - avg_middle


# Poisoning Detection

def detect_context_poisoning(text: str) -> List[Dict]:
    """
    Scan text for potential prompt injection/poisoning attempts.
    """
    patterns = [
        {"name": "ignore_instructions", "pattern": r"ignore\s+previously\s+instructions"},
        {"name": "new_persona", "pattern": r"you\s+are\s+now\s+a"},
        {"name": "jailbreak_attempt", "pattern": r"DAN\s+mode|developer\s+mode"}
    ]
    
    findings = []
    
    for p in patterns:
        matches = re.finditer(p["pattern"], text, re.IGNORECASE)
        for m in matches:
            findings.append({
                "type": p["name"],
                "position": m.start(),
                "snippet": text[max(0, m.start()-20):m.end()+20]
            })
            
    return findings
