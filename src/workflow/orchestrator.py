"""
Agent Orchestrator using LangGraph

Orchestrates multiple agents using LangGraph's StateGraph.
Provides workflow management with routing, execution, and state management.
"""

from typing import Dict, List, Optional, Any, Callable
from langgraph.graph import StateGraph, END
import logging
from datetime import datetime

from ..core.protocol import (
    WorkflowState,
    AgentStatus,
    AgentMessage,
    MessageType,
    AgentOutput,
)
from ..core.base_agent import BaseAgent
from ..core.router import RouterAgent


class AgentOrchestrator:
    """
    Orchestrates multiple agents using LangGraph StateGraph.
    
    The orchestrator:
    1. Routes queries to appropriate agents
    2. Manages workflow state
    3. Handles agent execution
    4. Coordinates multi-agent interactions
    """
    
    def __init__(
        self,
        router: RouterAgent,
        agents: List[BaseAgent],
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            router: Router agent for query routing
            agents: List of specialized agents
            config: Optional configuration
        """
        self.router = router
        self.agents = {agent.name: agent for agent in agents}
        self.config = config or {}
        self.logger = self._setup_logger()
        
        # Register all agents with the router
        self.router.register_agents(agents)
        
        # Build the LangGraph workflow
        self.workflow = self._build_workflow()
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logger for the orchestrator"""
        logger = logging.getLogger("orchestrator")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - ORCHESTRATOR - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph StateGraph for agent orchestration.
        
        Returns:
            Compiled StateGraph
        """
        # Create the state graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("router", self._router_node)
        workflow.add_node("execute_agent", self._execute_agent_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Define edges
        workflow.set_entry_point("router")
        
        # Router decides next step
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "execute": "execute_agent",
                "end": "finalize",
                "error": "finalize"
            }
        )
        
        # After execution, check if we need more agents
        workflow.add_conditional_edges(
            "execute_agent",
            self._after_execution_decision,
            {
                "continue": "router",
                "end": "finalize"
            }
        )
        
        # Finalize always ends
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _router_node(self, state: WorkflowState) -> WorkflowState:
        """
        Router node: Determines which agent should handle the query.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        self.logger.info("Router node: Analyzing query...")
        
        try:
            # Call router agent
            router_output = self.router.call(
                query=state.original_query,
                context=state.context,
                session_id=state.session_id
            )
            
            # Update state with routing decision
            if router_output.status == AgentStatus.SUCCESS:
                routing_result = router_output.result
                state.next_agent = routing_result.get("agent_name")
                state.routing_decision = routing_result
                
                # Create routing message
                message = self.router.create_message(
                    content=routing_result,
                    message_type=MessageType.INFO,
                    recipient=state.next_agent
                )
                state.messages.append(message)
                
                self.logger.info(f"Routed to agent: {state.next_agent}")
            else:
                self.logger.error(f"Router failed: {router_output.error}")
                state.next_agent = None
                state.final_status = AgentStatus.FAILED
                state.final_result = {"error": router_output.error}
            
        except Exception as e:
            self.logger.error(f"Router node error: {e}", exc_info=True)
            state.next_agent = None
            state.final_status = AgentStatus.FAILED
            state.final_result = {"error": str(e)}
        
        return state
    
    def _execute_agent_node(self, state: WorkflowState) -> WorkflowState:
        """
        Execute the selected agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        agent_name = state.next_agent
        
        if not agent_name or agent_name not in self.agents:
            self.logger.error(f"Invalid agent: {agent_name}")
            state.final_status = AgentStatus.FAILED
            state.final_result = {"error": f"Agent '{agent_name}' not found"}
            return state
        
        self.logger.info(f"Executing agent: {agent_name}")
        state.current_agent = agent_name
        state.iteration_count += 1
        
        try:
            agent = self.agents[agent_name]
            
            # Execute agent
            agent_output = agent.call(
                query=state.original_query,
                context=state.context,
                session_id=state.session_id,
                history=state.messages
            )
            
            # Store output
            state.agent_outputs[agent_name] = agent_output
            
            # Create response message
            message = agent.create_message(
                content={"output": agent_output.dict()},
                message_type=MessageType.RESPONSE,
                recipient="router"
            )
            state.messages.append(message)
            
            # Update context with agent results
            state.context[f"{agent_name}_result"] = agent_output.result
            
            self.logger.info(f"Agent '{agent_name}' completed with status: {agent_output.status}")
            
        except Exception as e:
            self.logger.error(f"Agent execution error: {e}", exc_info=True)
            
            # Store error output
            error_output = AgentOutput(
                agent_name=agent_name,
                status=AgentStatus.FAILED,
                result=None,
                error=str(e)
            )
            state.agent_outputs[agent_name] = error_output
        
        return state
    
    def _finalize_node(self, state: WorkflowState) -> WorkflowState:
        """
        Finalize the workflow and prepare final result.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        self.logger.info("Finalizing workflow...")
        
        state.is_complete = True
        
        # If final result not already set, aggregate agent outputs
        if state.final_result is None:
            state.final_result = self._aggregate_results(state)
        
        # Set final status if not already set
        if state.final_status == AgentStatus.IDLE:
            if state.agent_outputs:
                # Check if any agent succeeded
                successful = any(
                    output.status == AgentStatus.SUCCESS 
                    for output in state.agent_outputs.values()
                )
                state.final_status = AgentStatus.SUCCESS if successful else AgentStatus.FAILED
            else:
                state.final_status = AgentStatus.FAILED
        
        self.logger.info(f"Workflow complete. Status: {state.final_status}")
        
        return state
    
    def _route_decision(self, state: WorkflowState) -> str:
        """
        Decide where to go after routing.
        
        Args:
            state: Current workflow state
            
        Returns:
            Next node name
        """
        if state.final_status == AgentStatus.FAILED:
            return "error"
        
        if state.next_agent is None:
            return "end"
        
        if state.iteration_count >= state.max_iterations:
            self.logger.warning("Max iterations reached")
            return "end"
        
        return "execute"
    
    def _after_execution_decision(self, state: WorkflowState) -> str:
        """
        Decide whether to continue or end after agent execution.
        
        Args:
            state: Current workflow state
            
        Returns:
            Next node name
        """
        # Simple strategy: Execute one agent and end
        # Can be extended for multi-agent collaboration
        
        if state.iteration_count >= state.max_iterations:
            return "end"
        
        # Check if current agent suggests another agent
        if state.current_agent in state.agent_outputs:
            output = state.agent_outputs[state.current_agent]
            if isinstance(output.result, dict) and output.result.get("next_agent"):
                return "continue"
        
        # Default: end after one agent execution
        return "end"
    
    def _aggregate_results(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Aggregate results from all executed agents.
        
        Args:
            state: Current workflow state
            
        Returns:
            Aggregated results dictionary
        """
        aggregated = {
            "query": state.original_query,
            "session_id": state.session_id,
            "iterations": state.iteration_count,
            "agents_executed": list(state.agent_outputs.keys()),
            "results": {}
        }
        
        for agent_name, output in state.agent_outputs.items():
            aggregated["results"][agent_name] = {
                "status": output.status,
                "result": output.result,
                "confidence": output.confidence,
                "error": output.error
            }
        
        return aggregated
    
    def run(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Run the orchestrator workflow for a query.
        
        Args:
            query: User query
            session_id: Optional session identifier
            context: Optional context dictionary
            max_iterations: Maximum agent iterations
            
        Returns:
            Final workflow result
        """
        self.logger.info(f"Starting workflow for query: {query[:100]}...")
        
        # Initialize state
        initial_state = WorkflowState(
            original_query=query,
            session_id=session_id or f"session_{datetime.now().timestamp()}",
            context=context or {},
            max_iterations=max_iterations
        )
        
        # Run the workflow
        try:
            final_state = self.workflow.invoke(initial_state)

            # LangGraph may return either a WorkflowState instance or a dict
            if isinstance(final_state, dict):
                fs = final_state
                status = fs.get("final_status", AgentStatus.FAILED)
                result = fs.get("final_result")
                iterations = fs.get("iteration_count", fs.get("iterations", 0))
                agent_outputs = fs.get("agent_outputs", {}) or {}
                messages = fs.get("messages", []) or []
                agents_used = list(agent_outputs.keys()) if isinstance(agent_outputs, dict) else []
                messages_count = len(messages) if isinstance(messages, (list, tuple)) else 0
            else:
                fs = final_state
                status = fs.final_status
                result = fs.final_result
                iterations = fs.iteration_count
                agents_used = list(fs.agent_outputs.keys())
                messages_count = len(fs.messages)

            return {
                "status": status,
                "result": result,
                "metadata": {
                    "iterations": iterations,
                    "agents_used": agents_used,
                    "messages_count": messages_count,
                },
            }
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)
            return {
                "status": AgentStatus.FAILED,
                "result": None,
                "error": str(e)
            }


# ── Simple functional orchestrator (used by web_app/server.py) ────────────────

def process_query(question: str) -> dict:
    """
    Route *question* to the correct agent and return its answer.

    Routing is keyword-based via ``core/router``, with the dispatch table
    below wiring each agent name to the correct function signature.

    All calls are traced to LangSmith when LANGCHAIN_TRACING_V2=true and
    LANGCHAIN_API_KEY are set in .env.

    Parameters
    ----------
    question : str
        The user's question.

    Returns
    -------
    dict
        ``{"answer": str, "agent": str}``
    """
    # Local imports to avoid circular dependency issues at module load time
    from ..core.router import route_query
    from ..agents.finance_qa_agent.finance_agent import ask_finance_agent
    from ..agents.portfolio_analysis_agent.portfolio_agent import analyze_portfolio
    from ..agents.market_analysis_agent.market_agent import analyze_market
    from ..agents.tax_education_agent.tax_agent import explain_tax_concepts
    from ..agents.goal_planning_agent.goal_agent import plan_goals
    from ..agents.news_synthesizer_agent.news_agent import synthesize_news
    from ..utils.tracing import log_run

    agent_name = route_query(question)

    dispatch = {
        "finance_qa_agent":         lambda: ask_finance_agent(question),
        "portfolio_analysis_agent": lambda: analyze_portfolio({"assets": [], "question": question}),
        "market_analysis_agent":    lambda: analyze_market({"question": question}),
        "goal_planning_agent":      lambda: plan_goals({"question": question}),
        "news_synthesizer_agent":   lambda: synthesize_news([question]),
        "tax_education_agent":      lambda: explain_tax_concepts(question),
    }

    try:
        handler = dispatch.get(agent_name, dispatch["finance_qa_agent"])
        answer = handler()
        # ── LangSmith: log the top-level orchestrator run ───────────────────────
        log_run(
            name="process_query",
            inputs={"question": question, "routed_to": agent_name},
            outputs={"answer": answer[:200]},
            run_type="chain",
            tags=["orchestrator", agent_name],
        )
    except Exception as exc:  # noqa: BLE001
        # Graceful fallback to the general agent
        try:
            answer = ask_finance_agent(question)
            agent_name = "finance_qa_agent"
            log_run(
                name="process_query_fallback",
                inputs={"question": question},
                outputs={"answer": answer[:200]},
                run_type="chain",
                tags=["orchestrator", "fallback"],
                error=str(exc),
            )
        except Exception:
            raise exc  # re-raise original if fallback also fails

    return {"answer": answer, "agent": agent_name}
