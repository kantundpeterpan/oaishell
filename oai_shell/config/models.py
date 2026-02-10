from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CommandConfig(BaseModel):
    operationId: str
    description: Optional[str] = None
    mapping: Dict[str, str] = Field(default_factory=dict)
    after_call: Optional[Dict[str, Any]] = None

class StateConfig(BaseModel):
    storage: Optional[str] = None
    auto_inject: List[str] = Field(default_factory=list)
    defaults: Dict[str, Any] = Field(default_factory=dict)

class ShellConfig(BaseModel):
    name: str = "OAI-Shell"
    openapi_url: str
    base_url: Optional[str] = None
    commands: Dict[str, CommandConfig] = Field(default_factory=dict)
    state: StateConfig = Field(default_factory=StateConfig)
