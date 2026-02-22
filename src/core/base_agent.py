"""
BaseAgent Abstract Class

Provides the foundation for all agents in the multi-agent system.
All specialized agents should inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
import logging
from datetime import datetime
import uuid

from .protocol import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentMessage,
    MessageType,
    AgentMetadata,
    AgentCapability
)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    
    Each agent must implement:
    - _execute(): Core logic of the agent
    - get_metadata(): Agent information and capabilities
    
    Agents automatically handle:
    - Input/output validation
    - Error handling
    - Logging
    - Message creation
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the base agent.
        
        Args:
            name: Unique name for this agent
            description: Brief description of what this agent does
            config: Optional configuration dictionary
        """
        self.name = name
        self.description = description
        self.config = config or {}
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logger for this agent"""
        logger = logging.getLogger(f"agent.{self.name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.name} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    @abstractmethod
    def _execute(self, agent_input: AgentInput) -> Any:
        """
        Core execution logic for the agent.
        Must be implemented by all subclasses.
        
        Args:
            agent_input: Validated input following AgentInput schema
            
        Returns:
            Any result that will be wrapped in AgentOutput
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> AgentMetadata:
        """
        Return metadata describing this agent's capabilities.
        
        Returns:
            AgentMetadata with agent information
        """
        pass
    
    def get_input_schema(self) -> Type[BaseModel]:
        """
        Get the Pydantic schema for agent input.
        Can be overridden for custom input schemas.
        
        Returns:
            Pydantic model class for input validation
        """
        return AgentInput
    
    def get_output_schema(self) -> Type[BaseModel]:
        """
        Get the Pydantic schema for agent output.
        Can be overridden for custom output schemas.
        
        Returns:
            Pydantic model class for output validation
        """
        return AgentOutput
    
    def call(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        history: Optional[List[AgentMessage]] = None
    ) -> AgentOutput:
        """
        Main entry point for agent execution.
        Handles validation, execution, error handling, and output formatting.
        
        Args:
            query: The user query or task description
            context: Additional context for the agent
            session_id: Session identifier for tracking
            history: Previous messages in the conversation
            
        Returns:
            AgentOutput with execution results
        """
        start_time = datetime.now()
        
        try:
            # Create and validate input
            agent_input = self.get_input_schema()(
                query=query,
                context=context or {},
                session_id=session_id or str(uuid.uuid4()),
                history=history or []
            )
            
            self.logger.info(f"Executing agent with query: {query[:100]}...")
            
            # Execute agent logic
            result = self._execute(agent_input)
            
            # Create successful output
            output = AgentOutput(
                agent_name=self.name,
                status=AgentStatus.SUCCESS,
                result=result,
                confidence=self._calculate_confidence(result),
                metadata={
                    "execution_time": (datetime.now() - start_time).total_seconds(),
                    "config": self.config
                }
            )
            
            self.logger.info(f"Agent execution successful (confidence: {output.confidence})")
            return output
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
            
            # Create error output
            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                result=None,
                confidence=0.0,
                error=str(e),
                metadata={
                    "execution_time": (datetime.now() - start_time).total_seconds(),
                    "error_type": type(e).__name__
                }
            )
    
    def _calculate_confidence(self, result: Any) -> float:
        """
        Calculate confidence score for the result.
        Can be overridden by subclasses for custom confidence logic.
        
        Args:
            result: The result produced by the agent
            
        Returns:
            Confidence score between 0 and 1
        """
        # Default: 1.0 if result exists, 0.0 otherwise
        if result is None:
            return 0.0
        return 1.0
    
    def create_message(
        self,
        content: Dict[str, Any],
        message_type: MessageType = MessageType.RESPONSE,
        recipient: Optional[str] = None
    ) -> AgentMessage:
        """
        Create a standardized message from this agent.
        
        Args:
            content: Message payload
            message_type: Type of message
            recipient: Target agent (None for broadcast)
            
        Returns:
            AgentMessage object
        """
        return AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            content=content,
            metadata={"agent_description": self.description}
        )
    
    def validate_input(self, data: Dict[str, Any]) -> AgentInput:
        """
        Validate raw input data against the input schema.
        
        Args:
            data: Raw input dictionary
            
        Returns:
            Validated AgentInput object
            
        Raises:
            ValidationError if input is invalid
        """
        input_schema = self.get_input_schema()
        return input_schema(**data)
    
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle a given query.
        Returns a score between 0 (cannot handle) and 1 (perfect match).
        
        This is used by the router to decide which agent to invoke.
        Can be overridden by subclasses for custom routing logic.
        
        Args:
            query: The user query
            context: Additional context
            
        Returns:
            Score between 0 and 1
        """
        # Default implementation: check if any keywords match
        metadata = self.get_metadata()
        query_lower = query.lower()
        
        # Check examples
        for example in sum([cap.examples for cap in metadata.capabilities], []):
            if any(word in query_lower for word in example.lower().split()):
                return 0.7
        
        # Check capability descriptions
        for capability in metadata.capabilities:
            if any(word in query_lower for word in capability.description.lower().split()):
                return 0.5
        
        return 0.0
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"
