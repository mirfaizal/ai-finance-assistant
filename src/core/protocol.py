"""
Agent Communication Protocol

Defines the data structures and schemas for agent-to-agent communication
in the multi-agent finance assistant system.
"""

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Status of agent execution"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    WAITING = "waiting"


class MessageType(str, Enum):
    """Types of messages between agents"""
    QUERY = "query"
    RESPONSE = "response"
    ERROR = "error"
    INFO = "info"
    COMMAND = "command"


class AgentMessage(BaseModel):
    """
    Standard message format for inter-agent communication
    """
    message_id: str = Field(description="Unique identifier for the message")
    sender: str = Field(description="Name of the sending agent")
    recipient: Optional[str] = Field(None, description="Name of the recipient agent (None for broadcast)")
    message_type: MessageType = Field(description="Type of the message")
    content: Dict[str, Any] = Field(description="Message payload")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the message was created")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_001",
                "sender": "router",
                "recipient": "financial_analyst",
                "message_type": "query",
                "content": {"query": "What is the P/E ratio of AAPL?"},
                "timestamp": "2026-02-15T10:00:00",
                "metadata": {"priority": "high"}
            }
        }


class AgentInput(BaseModel):
    """
    Standard input schema for all agents
    """
    query: str = Field(description="The user query or task description")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the agent")
    session_id: Optional[str] = Field(None, description="Session identifier for tracking")
    history: List[AgentMessage] = Field(default_factory=list, description="Conversation history")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Analyze AAPL stock performance",
                "context": {"ticker": "AAPL", "timeframe": "1Y"},
                "session_id": "session_123"
            }
        }


class AgentOutput(BaseModel):
    """
    Standard output schema for all agents
    """
    agent_name: str = Field(description="Name of the agent that produced this output")
    status: AgentStatus = Field(description="Status of the agent execution")
    result: Any = Field(description="The actual result/output from the agent")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score (0-1)")
    error: Optional[str] = Field(None, description="Error message if status is FAILED")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the output was generated")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "financial_analyst",
                "status": "success",
                "result": {"pe_ratio": 28.5, "analysis": "Stock is fairly valued"},
                "confidence": 0.95,
                "metadata": {"sources": ["Alpha Vantage"]}
            }
        }


class WorkflowState(BaseModel):
    """
    Global state that flows through the entire LangGraph workflow
    """
    # Input
    original_query: str = Field(description="The original user query")
    session_id: str = Field(description="Unique session identifier")

    # Conversation memory (Step 1 / 5b)
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered list of prior {role, content} turns for this session",
    )
    memory_summary: Optional[str] = Field(
        None,
        description="Compressed memory summary from the memory synthesizer (replaces old raw turns)",
    )

    # Routing
    current_agent: Optional[str] = Field(None, description="Name of the currently active agent")
    next_agent: Optional[str] = Field(None, description="Name of the next agent to execute")
    routing_decision: Dict[str, Any] = Field(default_factory=dict, description="Router's decision context")

    # Communication
    messages: List[AgentMessage] = Field(default_factory=list, description="All messages exchanged")
    agent_outputs: Dict[str, AgentOutput] = Field(default_factory=dict, description="Outputs from each agent")

    # Context
    context: Dict[str, Any] = Field(default_factory=dict, description="Shared context across agents")

    # Control
    is_complete: bool = Field(default=False, description="Whether the workflow is complete")
    iteration_count: int = Field(default=0, description="Number of iterations/agent calls")
    max_iterations: int = Field(default=10, description="Maximum allowed iterations")

    # Final output
    final_result: Optional[Any] = Field(None, description="Final result to return to user")
    final_status: AgentStatus = Field(default=AgentStatus.IDLE, description="Final execution status")

    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "Analyze AAPL and suggest buy/sell",
                "session_id": "session_123",
                "current_agent": "financial_analyst",
                "is_complete": False,
                "iteration_count": 2
            }
        }


class AgentCapability(BaseModel):
    """
    Describes what an agent can do
    """
    name: str = Field(description="Name of the capability")
    description: str = Field(description="What this capability does")
    input_requirements: List[str] = Field(description="Required input parameters")
    output_format: str = Field(description="Description of output format")
    examples: List[str] = Field(default_factory=list, description="Example queries this handles")


class AgentMetadata(BaseModel):
    """
    Metadata about an agent
    """
    name: str = Field(description="Agent name")
    description: str = Field(description="What the agent does")
    version: str = Field(default="1.0.0", description="Agent version")
    capabilities: List[AgentCapability] = Field(description="List of agent capabilities")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    dependencies: List[str] = Field(default_factory=list, description="Names of agents this depends on")
