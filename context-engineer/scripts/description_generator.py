"""
Tool Description Generator

This module provides utilities for generating and evaluating tool descriptions
for agentic systems.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: List[ToolParameter]
    
    def to_json_schema(self) -> Dict:
        """Convert to JSON Schema format."""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


class ToolSchemaBuilder:
    """Builder for constructing tool definitions."""
    
    def __init__(self, name: str, description: str):
        self.tool = ToolDefinition(name, description, [])
    
    def add_param(self, name: str, type: str, description: str, 
                 required: bool = True, enum: List[str] = None):
        """Add a parameter to the tool."""
        self.tool.parameters.append(ToolParameter(
            name, type, description, required, enum
        ))
        return self
    
    def build(self) -> Dict:
        """Build and return JSON schema."""
        return self.tool.to_json_schema()


class ToolDescriptionEvaluator:
    """Evaluate tool descriptions against best practices."""
    
    def evaluate(self, tool_def: Dict) -> Dict:
        """
        Evaluate a tool definition.
        
        Checks:
        1. Clarity: Is description unambiguous?
        2. Completeness: Are all params described?
        3. Constraints: are limitations specified?
        """
        issues = []
        score = 1.0
        
        name = tool_def.get("name", "")
        desc = tool_def.get("description", "")
        
        # Check description length
        if len(desc) < 20:
            issues.append("Description too short (< 20 chars)")
            score -= 0.2
        
        # Check for constraint markers
        constraints = ["only", "must", "cannot", "limit", "max", "min"]
        has_constraints = any(c in desc.lower() for c in constraints)
        if not has_constraints:
            issues.append("No explicit constraints found in description")
            score -= 0.1
            
        # Check parameter descriptions
        params = tool_def.get("input_schema", {}).get("properties", {})
        for pname, pdef in params.items():
            pdesc = pdef.get("description", "")
            if len(pdesc) < 10:
                issues.append(f"Parameter '{pname}' description too short")
                score -= 0.1
                
        return {
            "name": name,
            "score": max(0.0, score),
            "issues": issues,
            "passed": score > 0.7
        }


# Templates

TEMPLATES = {
    "file_read": """
    Read the contents of a file from the filesystem.
    
    Use this tool when you need to examine the source code, configuration,
    or data within a file.
    
    Limitations:
    - Cannot read binary files directly (returns placeholder)
    - Max size 100KB per read
    """,
    "file_write": """
    Create or overwrite a file with new content.
    
    Use this tool to save your work, create new modules, or update configuration.
    
    Constraints:
    - Path must be absolute
    - Directory must exist (use mkdir first)
    - Will overwrite without confirmation
    """
}

def get_template(name: str) -> Optional[str]:
    """Get a description template."""
    return TEMPLATES.get(name)
