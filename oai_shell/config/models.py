from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class FieldConfig(BaseModel):
    path: str
    label: Optional[str] = None
    style: Optional[str] = None
    format: str = "text"  # text, json, markdown
    optional: bool = False

class FormattingBlockConfig(BaseModel):
    title: Optional[str] = None
    path: str = ""
    layout: str = "list"  # list, table, markdown, json
    fields: List[FieldConfig] = Field(default_factory=list)
    optional: bool = False

class ResponseFormattingConfig(BaseModel):
    title: Optional[str] = None
    blocks: List[FormattingBlockConfig] = Field(default_factory=list)

class CommandConfig(BaseModel):
    operationId: str
    description: Optional[str] = None
    mapping: Dict[str, str] = Field(default_factory=dict)
    after_call: Optional[Dict[str, Any]] = None
    default_response_field: Optional[str] = None
    force_response_field: bool = False
    formatting: Optional[ResponseFormattingConfig] = None

class StateConfig(BaseModel):
    storage: Optional[str] = None
    auto_inject: List[str] = Field(default_factory=list)
    defaults: Dict[str, Any] = Field(default_factory=dict)

class TUIConfig(BaseModel):
    aggregation_depth: int = Field(default=1, ge=0)
    type_icons: Dict[str, str] = Field(default_factory=lambda: {
        "object": "📦",
        "array": "📜",
        "string": "🔤",
        "integer": "🔢",
        "number": "🔢",
        "boolean": "☯️",
        "default": "📄"
    })

class ShellConfig(BaseModel):
    name: str = "OAI-Shell"
    openapi_url: str = "/openapi.json"
    base_url: Optional[str] = None
    commands: Dict[str, CommandConfig] = Field(default_factory=dict)
    state: StateConfig = Field(default_factory=StateConfig)
    tui: TUIConfig = Field(default_factory=TUIConfig)
