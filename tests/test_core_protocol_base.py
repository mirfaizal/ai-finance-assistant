"""Unit tests for src/core/protocol.py and src/core/base_agent.py"""
from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Protocol models
# ══════════════════════════════════════════════════════════════════════════════

class TestProtocolModels:

    def test_agent_status_values(self):
        from src.core.protocol import AgentStatus
        assert AgentStatus.SUCCESS == "success"
        assert AgentStatus.FAILED  == "failed"
        assert AgentStatus.IDLE    == "idle"
        assert AgentStatus.RUNNING == "running"

    def test_message_type_values(self):
        from src.core.protocol import MessageType
        assert MessageType.QUERY    == "query"
        assert MessageType.RESPONSE == "response"
        assert MessageType.ERROR    == "error"

    def test_agent_message_creation(self):
        from src.core.protocol import AgentMessage, MessageType
        msg = AgentMessage(
            message_id="msg-001",
            sender="router",
            message_type=MessageType.QUERY,
            content={"q": "hello"},
        )
        assert msg.sender == "router"
        assert msg.content == {"q": "hello"}
        assert msg.recipient is None

    def test_agent_message_with_recipient(self):
        from src.core.protocol import AgentMessage, MessageType
        msg = AgentMessage(
            message_id="msg-002",
            sender="router",
            recipient="stock_agent",
            message_type=MessageType.QUERY,
            content={"query": "AAPL price"},
        )
        assert msg.recipient == "stock_agent"

    def test_agent_input_defaults(self):
        from src.core.protocol import AgentInput
        inp = AgentInput(query="What is a bond?")
        assert inp.query == "What is a bond?"
        assert inp.context == {}
        assert inp.history == []

    def test_agent_input_with_context(self):
        from src.core.protocol import AgentInput
        inp = AgentInput(query="analyze AAPL", context={"ticker": "AAPL"}, session_id="sess-1")
        assert inp.context["ticker"] == "AAPL"
        assert inp.session_id == "sess-1"

    def test_agent_output_success(self):
        from src.core.protocol import AgentOutput, AgentStatus
        out = AgentOutput(
            agent_name="test_agent",
            status=AgentStatus.SUCCESS,
            result={"answer": "42"},
        )
        assert out.status == AgentStatus.SUCCESS
        assert out.result["answer"] == "42"
        assert out.error is None

    def test_agent_output_failure(self):
        from src.core.protocol import AgentOutput, AgentStatus
        out = AgentOutput(
            agent_name="test_agent",
            status=AgentStatus.FAILED,
            result=None,
            error="Something went wrong",
        )
        assert out.status == AgentStatus.FAILED
        assert out.error == "Something went wrong"

    def test_agent_output_confidence_range(self):
        from src.core.protocol import AgentOutput, AgentStatus
        out = AgentOutput(
            agent_name="a",
            status=AgentStatus.SUCCESS,
            result="ok",
            confidence=0.85,
        )
        assert 0.0 <= out.confidence <= 1.0

    def test_workflow_state_defaults(self):
        from src.core.protocol import WorkflowState, AgentStatus
        state = WorkflowState(
            original_query="What is inflation?",
            session_id="sess-001",
        )
        assert state.is_complete is False
        assert state.iteration_count == 0
        assert state.final_status == AgentStatus.IDLE
        assert state.messages == []

    def test_workflow_state_complete(self):
        from src.core.protocol import WorkflowState, AgentStatus
        state = WorkflowState(
            original_query="Test",
            session_id="s1",
            is_complete=True,
            final_status=AgentStatus.SUCCESS,
            final_result={"answer": "42"},
        )
        assert state.is_complete is True
        assert state.final_result["answer"] == "42"

    def test_agent_capability(self):
        from src.core.protocol import AgentCapability
        cap = AgentCapability(
            name="stock_analysis",
            description="Analyzes stocks",
            input_requirements=["ticker"],
            output_format="JSON with price data",
            examples=["What is AAPL stock price?"],
        )
        assert cap.name == "stock_analysis"
        assert "ticker" in cap.input_requirements

    def test_agent_metadata(self):
        from src.core.protocol import AgentMetadata, AgentCapability
        cap = AgentCapability(
            name="cap1",
            description="does stuff",
            input_requirements=["q"],
            output_format="str",
        )
        meta = AgentMetadata(
            name="my_agent",
            description="A test agent",
            capabilities=[cap],
            tags=["test"],
        )
        assert meta.name == "my_agent"
        assert len(meta.capabilities) == 1


# ══════════════════════════════════════════════════════════════════════════════
# BaseAgent tests (via a concrete subclass)
# ══════════════════════════════════════════════════════════════════════════════

def _make_concrete_agent(name="test_agent", description="A test agent"):
    """Create a concrete subclass of BaseAgent for testing."""
    from src.core.base_agent import BaseAgent
    from src.core.protocol import AgentInput, AgentMetadata, AgentCapability

    class ConcreteAgent(BaseAgent):
        def _execute(self, agent_input: AgentInput):
            return {"answer": f"handled: {agent_input.query}"}

        def get_metadata(self) -> AgentMetadata:
            cap = AgentCapability(
                name="general",
                description="handles questions",
                input_requirements=["query"],
                output_format="dict",
                examples=["What is a bond?"],
            )
            return AgentMetadata(name=self.name, description=self.description, capabilities=[cap])

    return ConcreteAgent(name=name, description=description)


class TestBaseAgent:

    def test_call_returns_agent_output(self):
        from src.core.protocol import AgentStatus
        agent = _make_concrete_agent()
        output = agent.call(query="What is inflation?", session_id="s1")
        assert output.status == AgentStatus.SUCCESS
        assert output.result is not None

    def test_call_sets_agent_name(self):
        agent = _make_concrete_agent(name="finance_qa")
        output = agent.call(query="test")
        assert output.agent_name == "finance_qa"

    def test_call_handles_exception(self):
        from src.core.base_agent import BaseAgent
        from src.core.protocol import AgentInput, AgentMetadata, AgentCapability, AgentStatus

        class FailingAgent(BaseAgent):
            def _execute(self, agent_input: AgentInput):
                raise RuntimeError("execution failed")

            def get_metadata(self):
                cap = AgentCapability(name="x", description="x", input_requirements=[], output_format="x")
                return AgentMetadata(name=self.name, description="fails", capabilities=[cap])

        agent = FailingAgent(name="failer", description="fails")
        output = agent.call(query="test")
        assert output.status == AgentStatus.FAILED
        assert output.error is not None

    def test_create_message(self):
        from src.core.protocol import MessageType
        agent = _make_concrete_agent()
        msg = agent.create_message(
            content={"data": "hello"},
            message_type=MessageType.RESPONSE,
            recipient="router",
        )
        assert msg.sender == "test_agent"
        assert msg.recipient == "router"
        assert msg.content == {"data": "hello"}

    def test_get_metadata(self):
        agent = _make_concrete_agent()
        meta = agent.get_metadata()
        assert meta.name == "test_agent"
        assert len(meta.capabilities) >= 1

    def test_str_repr(self):
        agent = _make_concrete_agent()
        assert "test_agent" in str(agent)
        assert "test_agent" in repr(agent)

    def test_can_handle_matching_keyword(self):
        agent = _make_concrete_agent()
        score = agent.can_handle("What is a bond?")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_validate_input(self):
        agent = _make_concrete_agent()
        inp = agent.validate_input({"query": "What is inflation?", "session_id": "s1"})
        assert inp.query == "What is inflation?"

    def test_get_input_schema_returns_agent_input(self):
        from src.core.protocol import AgentInput
        agent = _make_concrete_agent()
        assert agent.get_input_schema() is AgentInput

    def test_get_output_schema_returns_agent_output(self):
        from src.core.protocol import AgentOutput
        agent = _make_concrete_agent()
        assert agent.get_output_schema() is AgentOutput

    def test_confidence_zero_for_none_result(self):
        from src.core.base_agent import BaseAgent
        from src.core.protocol import AgentInput, AgentMetadata, AgentCapability

        class NoneResultAgent(BaseAgent):
            def _execute(self, agent_input: AgentInput):
                return None
            def get_metadata(self):
                cap = AgentCapability(name="x", description="x", input_requirements=[], output_format="x")
                return AgentMetadata(name=self.name, description="x", capabilities=[cap])

        agent = NoneResultAgent(name="null_agent", description="returns None")
        output = agent.call(query="test")
        assert output.confidence == 0.0

    def test_confidence_one_for_non_none_result(self):
        agent = _make_concrete_agent()
        output = agent.call(query="What is a bond?")
        assert output.confidence == 1.0

    def test_call_with_context(self):
        agent = _make_concrete_agent()
        output = agent.call(query="test", context={"key": "value"})
        assert output.result is not None

    def test_config_defaults_to_empty_dict(self):
        agent = _make_concrete_agent()
        assert agent.config == {}

    def test_config_stored(self):
        from src.core.base_agent import BaseAgent
        from src.core.protocol import AgentInput, AgentMetadata, AgentCapability

        class ConfigAgent(BaseAgent):
            def _execute(self, ai): return "ok"
            def get_metadata(self):
                cap = AgentCapability(name="x", description="x", input_requirements=[], output_format="x")
                return AgentMetadata(name=self.name, description="x", capabilities=[cap])

        agent = ConfigAgent(name="cfg", description="x", config={"timeout": 30})
        assert agent.config["timeout"] == 30
