"""
Reasoning Runtime Module

Provides logical reasoning, chain-of-thought, planning, problem-solving,
and decision-making capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union
import asyncio
import logging
import uuid

from runtime.base.module import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.runtime import Runtime

logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    """Types of reasoning."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"
    LOGICAL = "logical"
    MATHEMATICAL = "mathematical"
    COMMONSENSE = "commonsense"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    PROBABILISTIC = "probabilistic"
    COUNTERFACTUAL = "counterfactual"


class ReasoningMethod(Enum):
    """Reasoning methods/techniques."""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    GRAPH_OF_THOUGHTS = "graph_of_thoughts"
    PROGRAM_OF_THOUGHTS = "program_of_thoughts"
    REACT = "react"  # Reasoning + Acting
    SELF_CONSISTENCY = "self_consistency"
    MAJORITY_VOTE = "majority_vote"
    STEP_BY_STEP = "step_by_step"
    SKELETON_OF_THOUGHT = "skeleton_of_thought"
    LEAST_TO_MOST = "least_to_most"
    DECOMPOSITION = "decomposition"
    VERIFICATION = "verification"
    CRITIQUE = "critique"
    REFLECTION = "reflection"


class PlanningMethod(Enum):
    """Planning methods."""
    HTN = "htn"  # Hierarchical Task Network
    STRIPS = "strips"
    PDDL = "pddl"
    GRAPH_PLAN = "graph_plan"
    LLM_PLANNING = "llm_planning"
    REACT = "react"
    REFLEXION = "reflexion"
    AUTO_GPT = "auto_gpt"
    BABY_AGI = "baby_agi"
    PLAN_AND_EXECUTE = "plan_and_execute"


class ProblemType(Enum):
    """Problem types for reasoning."""
    LOGIC_PUZZLE = "logic_puzzle"
    MATH_WORD_PROBLEM = "math_word_problem"
    CODING = "coding"
    DEBUGGING = "debugging"
    RAVEN_MATRICES = "raven_matrices"
    COMMONSENSE_QA = "commonsense_qa"
    MULTI_HOP_QA = "multi_hop_qa"
    DECISION_MAKING = "decision_making"
    RESOURCE_ALLOCATION = "resource_allocation"
    SCHEDULING = "scheduling"
    PATHFINDING = "pathfinding"
    CONSTRAINT_SATISFACTION = "constraint_satisfaction"
    GAME_PLAYING = "game_playing"
    STRATEGY = "strategy"
    CUSTOM = "custom"


@dataclass
class ReasoningStep:
    """Single step in reasoning chain."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_number: int = 0
    description: str = ""
    reasoning: str = ""
    conclusion: str = ""
    confidence: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReasoningChain:
    """Chain of reasoning steps."""
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    problem: str = ""
    steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: str = ""
    confidence: float = 0.0
    method: ReasoningMethod = ReasoningMethod.CHAIN_OF_THOUGHT
    total_time: float = 0.0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReasoningTree:
    """Tree of reasoning paths (for Tree of Thoughts)."""
    tree_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    problem: str = ""
    root: Optional[ReasoningStep] = None
    nodes: Dict[str, ReasoningStep] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=dict)  # parent -> children
    best_path: List[str] = field(default_factory=list)
    method: ReasoningMethod = ReasoningMethod.TREE_OF_THOUGHTS
    total_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Plan:
    """Planning result."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    estimated_time: float = 0.0
    resources_required: Dict[str, Any] = field(default_factory=dict)
    success_criteria: List[str] = field(default_factory=list)
    contingency_plans: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    method: PlanningMethod = PlanningMethod.LLM_PLANNING
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionResult:
    """Plan execution result."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    plan_id: str = ""
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = False
    final_output: Any = None
    errors: List[str] = field(default_factory=list)
    total_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DecisionOption:
    """Option in decision making."""
    option_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    score: float = 0.0
    risks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionResult:
    """Decision making result."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    problem: str = ""
    options: List[DecisionOption] = field(default_factory=list)
    chosen_option: Optional[DecisionOption] = None
    reasoning: str = ""
    confidence: float = 0.0
    method: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VerificationResult:
    """Verification/critique result."""
    verification_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target: str = ""  # What was verified
    passed: bool = False
    score: float = 0.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class ReasoningBackend(ABC):
    """Abstract base class for reasoning backends."""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass


class ChainOfThoughtBackend(ReasoningBackend):
    """Chain of Thought reasoning backend."""

    @abstractmethod
    async def reason(
        self,
        problem: str,
        context: Optional[str] = None,
        examples: Optional[List[Dict[str, str]]] = None,
        max_steps: int = 10,
        **kwargs
    ) -> ReasoningChain:
        pass

    @abstractmethod
    async def reason_step_by_step(
        self,
        problem: str,
        **kwargs
    ) -> ReasoningChain:
        pass


class TreeOfThoughtsBackend(ReasoningBackend):
    """Tree of Thoughts reasoning backend."""

    @abstractmethod
    async def reason(
        self,
        problem: str,
        branching_factor: int = 3,
        max_depth: int = 5,
        pruning_threshold: float = 0.3,
        **kwargs
    ) -> ReasoningTree:
        pass


class PlanningBackend(ReasoningBackend):
    """Planning backend."""

    @abstractmethod
    async def create_plan(
        self,
        goal: str,
        context: Optional[str] = None,
        constraints: Optional[List[str]] = None,
        available_actions: Optional[List[str]] = None,
        **kwargs
    ) -> Plan:
        pass

    @abstractmethod
    async def execute_plan(
        self,
        plan: Plan,
        executor: Any,
        **kwargs
    ) -> ExecutionResult:
        pass

    @abstractmethod
    async def replan(
        self,
        plan: Plan,
        execution_result: ExecutionResult,
        **kwargs
    ) -> Plan:
        pass


class VerificationBackend(ReasoningBackend):
    """Verification/critique backend."""

    @abstractmethod
    async def verify(
        self,
        claim: str,
        evidence: Optional[List[str]] = None,
        context: Optional[str] = None,
        **kwargs
    ) -> VerificationResult:
        pass

    @abstractmethod
    async def critique(
        self,
        solution: str,
        problem: str,
        criteria: Optional[List[str]] = None,
        **kwargs
    ) -> VerificationResult:
        pass


class DecisionBackend(ReasoningBackend):
    """Decision making backend."""

    @abstractmethod
    async def decide(
        self,
        problem: str,
        options: List[DecisionOption],
        criteria: Optional[List[str]] = None,
        context: Optional[str] = None,
        **kwargs
    ) -> DecisionResult:
        pass


class MathReasoningBackend(ReasoningBackend):
    """Mathematical reasoning backend."""

    @abstractmethod
    async def solve(
        self,
        problem: str,
        method: Optional[ReasoningMethod] = None,
        show_work: bool = True,
        **kwargs
    ) -> ReasoningChain:
        pass


class LogicReasoningBackend(ReasoningBackend):
    """Logical reasoning backend."""

    @abstractmethod
    async def solve(
        self,
        premises: List[str],
        conclusion: str,
        **kwargs
    ) -> VerificationResult:
        pass

    @abstractmethod
    async def prove(
        self,
        theorem: str,
        axioms: List[str],
        **kwargs
    ) -> ReasoningChain:
        pass


class ReasoningModule(RuntimeModule):
    """
    Reasoning Runtime Module

    Provides comprehensive reasoning capabilities:
    - Chain of Thought reasoning
    - Tree of Thoughts
    - Graph of Thoughts
    - Planning (HTN, STRIPS, LLM-based)
    - Execution with ReAct pattern
    - Verification and critique
    - Decision making
    - Mathematical reasoning
    - Logical reasoning
    - Self-reflection and improvement
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="reasoning",
            version="1.0.0",
            description="Logical reasoning: CoT, ToT, planning, verification, decision making, math, logic, reflection",
            author="AIPENSA",
            dependencies=[],
            provides=["cot", "tot", "planning", "verification", "decision", "math", "logic"],
            tags={"reasoning", "chain-of-thought", "tree-of-thoughts", "planning", "math", "logic"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Backends
        self._cot_backend: Optional[ChainOfThoughtBackend] = None
        self._tot_backend: Optional[TreeOfThoughtsBackend] = None
        self._planning_backend: Optional[PlanningBackend] = None
        self._verification_backend: Optional[VerificationBackend] = None
        self._decision_backend: Optional[DecisionBackend] = None
        self._math_backend: Optional[MathReasoningBackend] = None
        self._logic_backend: Optional[LogicReasoningBackend] = None

        # Configuration
        self._default_method = ReasoningMethod(config.get("default_method", "chain_of_thought"))
        self._max_steps = config.get("max_steps", 10)
        self._enable_verification = config.get("enable_verification", True)
        self._enable_reflection = config.get("enable_reflection", True)

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize reasoning backends."""
        await super().initialize(runtime, config)

        config = self.config

        # Chain of Thought backend
        cot_config = config.get("chain_of_thought", {})
        backend_type = cot_config.get("backend", "mock")
        if backend_type == "mock":
            self._cot_backend = MockChainOfThoughtBackend()
        await self._cot_backend.initialize(cot_config)

        # Tree of Thoughts backend
        tot_config = config.get("tree_of_thoughts", {})
        backend_type = tot_config.get("backend", "mock")
        if backend_type == "mock":
            self._tot_backend = MockTreeOfThoughtsBackend()
        await self._tot_backend.initialize(tot_config)

        # Planning backend
        plan_config = config.get("planning", {})
        backend_type = plan_config.get("backend", "mock")
        if backend_type == "mock":
            self._planning_backend = MockPlanningBackend()
        await self._planning_backend.initialize(plan_config)

        # Verification backend
        verify_config = config.get("verification", {})
        backend_type = verify_config.get("backend", "mock")
        if backend_type == "mock":
            self._verification_backend = MockVerificationBackend()
        await self._verification_backend.initialize(verify_config)

        # Decision backend
        decision_config = config.get("decision", {})
        backend_type = decision_config.get("backend", "mock")
        if backend_type == "mock":
            self._decision_backend = MockDecisionBackend()
        await self._decision_backend.initialize(decision_config)

        # Math reasoning backend
        math_config = config.get("math_reasoning", {})
        backend_type = math_config.get("backend", "mock")
        if backend_type == "mock":
            self._math_backend = MockMathReasoningBackend()
        await self._math_backend.initialize(math_config)

        # Logic reasoning backend
        logic_config = config.get("logic_reasoning", {})
        backend_type = logic_config.get("backend", "mock")
        if backend_type == "mock":
            self._logic_backend = MockLogicReasoningBackend()
        await self._logic_backend.initialize(logic_config)

        logger.info("Reasoning module initialized with all backends")

    async def start(self) -> None:
        """Start reasoning module."""
        await super().start()
        logger.info("Reasoning module started")

    async def stop(self) -> None:
        """Stop reasoning module and cleanup backends."""
        for backend in [
            self._cot_backend, self._tot_backend, self._planning_backend,
            self._verification_backend, self._decision_backend,
            self._math_backend, self._logic_backend
        ]:
            if backend:
                await backend.cleanup()

        await super().stop()
        logger.info("Reasoning module stopped")

    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Cleanup backends
        for backend in [
            self._cot_backend, self._tot_backend, self._planning_backend,
            self._verification_backend, self._decision_backend,
            self._math_backend, self._logic_backend
        ]:
            if backend:
                await backend.cleanup()

        await super().cleanup()
        logger.info("Reasoning module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all backends."""
        health = await super().health_check()
        health["backends"] = {}

        for name, backend in [
            ("chain_of_thought", self._cot_backend),
            ("tree_of_thoughts", self._tot_backend),
            ("planning", self._planning_backend),
            ("verification", self._verification_backend),
            ("decision", self._decision_backend),
            ("math_reasoning", self._math_backend),
            ("logic_reasoning", self._logic_backend)
        ]:
            if backend:
                health["backends"][name] = await backend.health_check()
            else:
                health["backends"][name] = {"status": "not_initialized"}

        all_healthy = all(
            b.get("status") == "healthy"
            for b in health["backends"].values()
        )
        health["status"] = "healthy" if all_healthy else "degraded"
        return health

    # Chain of Thought Operations
    async def reason(
        self,
        problem: str,
        context: Optional[str] = None,
        examples: Optional[List[Dict[str, str]]] = None,
        method: ReasoningMethod = ReasoningMethod.CHAIN_OF_THOUGHT,
        max_steps: Optional[int] = None,
        **kwargs
    ) -> ReasoningChain:
        """Perform chain of thought reasoning."""
        if not self._cot_backend:
            raise RuntimeError("Chain of Thought backend not initialized")

        if method == ReasoningMethod.CHAIN_OF_THOUGHT:
            return await self._cot_backend.reason(
                problem, context, examples, max_steps or self._max_steps, **kwargs
            )
        elif method == ReasoningMethod.STEP_BY_STEP:
            return await self._cot_backend.reason_step_by_step(problem, **kwargs)
        elif method == ReasoningMethod.LEAST_TO_MOST:
            # Decompose into subproblems then solve
            return await self._least_to_most_reason(problem, **kwargs)
        else:
            raise ValueError(f"Method {method} not supported by CoT backend")

    async def _least_to_most_reason(self, problem: str, **kwargs) -> ReasoningChain:
        """Least-to-most reasoning: decompose then solve."""
        # First decompose
        decomp_prompt = f"Decompose this problem into simpler subproblems:\n{problem}"
        decomp_result = await self._cot_backend.reason(decomp_prompt, **kwargs)

        # Then solve each subproblem
        final_chain = ReasoningChain(problem=problem, method=ReasoningMethod.LEAST_TO_MOST)
        for step in decomp_result.steps:
            sub_result = await self._cot_backend.reason(step.conclusion, **kwargs)
            final_chain.steps.extend(sub_result.steps)

        return final_chain

    # Tree of Thoughts Operations
    async def reason_tree(
        self,
        problem: str,
        branching_factor: int = 3,
        max_depth: int = 5,
        pruning_threshold: float = 0.3,
        **kwargs
    ) -> ReasoningTree:
        """Perform Tree of Thoughts reasoning."""
        if not self._tot_backend:
            raise RuntimeError("Tree of Thoughts backend not initialized")
        return await self._tot_backend.reason(
            problem, branching_factor, max_depth, pruning_threshold, **kwargs
        )

    # Planning Operations
    async def create_plan(
        self,
        goal: str,
        context: Optional[str] = None,
        constraints: Optional[List[str]] = None,
        available_actions: Optional[List[str]] = None,
        method: PlanningMethod = PlanningMethod.LLM_PLANNING,
        **kwargs
    ) -> Plan:
        """Create a plan to achieve a goal."""
        if not self._planning_backend:
            raise RuntimeError("Planning backend not initialized")
        return await self._planning_backend.create_plan(
            goal, context, constraints, available_actions, **kwargs
        )

    async def execute_plan(
        self,
        plan: Plan,
        executor: Any,
        **kwargs
    ) -> ExecutionResult:
        """Execute a plan."""
        if not self._planning_backend:
            raise RuntimeError("Planning backend not initialized")
        return await self._planning_backend.execute_plan(plan, executor, **kwargs)

    async def plan_and_execute(
        self,
        goal: str,
        executor: Any,
        context: Optional[str] = None,
        max_replans: int = 3,
        **kwargs
    ) -> ExecutionResult:
        """Create plan and execute with replanning on failure."""
        plan = await self.create_plan(goal, context, **kwargs)

        for attempt in range(max_replans + 1):
            result = await self.execute_plan(plan, executor, **kwargs)
            if result.success:
                return result

            if attempt < max_replans:
                logger.info(f"Plan execution failed, replanning (attempt {attempt + 1})")
                plan = await self._planning_backend.replan(plan, result, **kwargs)
            else:
                return result

        return result

    # Verification Operations
    async def verify(
        self,
        claim: str,
        evidence: Optional[List[str]] = None,
        context: Optional[str] = None,
        **kwargs
    ) -> VerificationResult:
        """Verify a claim."""
        if not self._verification_backend:
            raise RuntimeError("Verification backend not initialized")
        return await self._verification_backend.verify(claim, evidence, context, **kwargs)

    async def critique(
        self,
        solution: str,
        problem: str,
        criteria: Optional[List[str]] = None,
        **kwargs
    ) -> VerificationResult:
        """Critique a solution."""
        if not self._verification_backend:
            raise RuntimeError("Verification backend not initialized")
        return await self._verification_backend.critique(solution, problem, criteria, **kwargs)

    async def self_consistency_check(
        self,
        problem: str,
        n_samples: int = 5,
        **kwargs
    ) -> ReasoningChain:
        """Self-consistency: sample multiple reasoning paths and take majority."""
        chains = []
        for _ in range(n_samples):
            chain = await self.reason(problem, **kwargs)
            chains.append(chain)

        # Simple majority vote on final answer
        answers = [c.final_answer for c in chains]
        from collections import Counter
        most_common = Counter(answers).most_common(1)[0][0]

        # Return best chain with majority answer
        best_chain = next(c for c in chains if c.final_answer == most_common)
        best_chain.method = ReasoningMethod.SELF_CONSISTENCY
        best_chain.metadata["all_answers"] = answers
        best_chain.metadata["consensus"] = most_common
        return best_chain

    # Decision Making Operations
    async def decide(
        self,
        problem: str,
        options: List[DecisionOption],
        criteria: Optional[List[str]] = None,
        context: Optional[str] = None,
        **kwargs
    ) -> DecisionResult:
        """Make a decision among options."""
        if not self._decision_backend:
            raise RuntimeError("Decision backend not initialized")
        return await self._decision_backend.decide(problem, options, criteria, context, **kwargs)

    async def analyze_options(
        self,
        options: List[DecisionOption],
        criteria: List[str],
        **kwargs
    ) -> List[DecisionOption]:
        """Analyze and score options against criteria."""
        if not self._decision_backend:
            raise RuntimeError("Decision backend not initialized")
        # This would use the decision backend to score each option
        for option in options:
            result = await self._decision_backend.decide(
                f"Score option: {option.name}", [option], criteria, **kwargs
            )
            option.score = result.chosen_option.score if result.chosen_option else 0
        return options

    # Mathematical Reasoning Operations
    async def solve_math(
        self,
        problem: str,
        method: Optional[ReasoningMethod] = None,
        show_work: bool = True,
        **kwargs
    ) -> ReasoningChain:
        """Solve a mathematical problem."""
        if not self._math_backend:
            raise RuntimeError("Math reasoning backend not initialized")
        return await self._math_backend.solve(problem, method, show_work, **kwargs)

    # Logical Reasoning Operations
    async def logic_prove(
        self,
        theorem: str,
        axioms: List[str],
        **kwargs
    ) -> ReasoningChain:
        """Prove a theorem from axioms."""
        if not self._logic_backend:
            raise RuntimeError("Logic reasoning backend not initialized")
        return await self._logic_backend.prove(theorem, axioms, **kwargs)

    async def logic_verify(
        self,
        premises: List[str],
        conclusion: str,
        **kwargs
    ) -> VerificationResult:
        """Verify a logical conclusion from premises."""
        if not self._logic_backend:
            raise RuntimeError("Logic reasoning backend not initialized")
        return await self._logic_backend.solve(premises, conclusion, **kwargs)

    # ReAct: Reasoning + Acting
    async def react(
        self,
        task: str,
        tools: Dict[str, Any],
        max_iterations: int = 10,
        **kwargs
    ) -> ReasoningChain:
        """ReAct: Reasoning + Acting pattern."""
        chain = ReasoningChain(problem=task, method=ReasoningMethod.REACT)

        for iteration in range(max_iterations):
            # Reason: think about what to do next
            thought_prompt = f"""
Task: {task}
Previous steps: {[s.reasoning for s in chain.steps]}
Available tools: {list(tools.keys())}

Think about what to do next. Format:
Thought: <your reasoning>
Action: <tool_name>
Action Input: <input>
"""
            thought_result = await self._cot_backend.reason(thought_prompt, **kwargs)
            chain.steps.extend(thought_result.steps)

            # Extract action from last step
            last_step = chain.steps[-1] if chain.steps else None
            if not last_step:
                break

            # Parse action (simplified)
            if "Action:" in last_step.reasoning:
                action_line = [l for l in last_step.reasoning.split('\n') if l.startswith('Action:')]
                if action_line:
                    tool_name = action_line[0].replace('Action:', '').strip()
                    if tool_name in tools:
                        # Act
                        action_input_line = [l for l in last_step.reasoning.split('\n') if l.startswith('Action Input:')]
                        action_input = action_input_line[0].replace('Action Input:', '').strip() if action_input_line else ""

                        try:
                            observation = await tools[tool_name](action_input)
                            obs_step = ReasoningStep(
                                step_number=len(chain.steps) + 1,
                                description=f"Observation from {tool_name}",
                                reasoning=str(observation),
                                conclusion=f"Tool {tool_name} returned: {observation}"
                            )
                            chain.steps.append(obs_step)
                        except Exception as e:
                            error_step = ReasoningStep(
                                step_number=len(chain.steps) + 1,
                                description=f"Error calling {tool_name}",
                                reasoning=str(e),
                                conclusion=f"Error: {e}"
                            )
                            chain.steps.append(error_step)

            # Check for final answer
            if "Final Answer:" in last_step.reasoning:
                chain.final_answer = last_step.reasoning.split("Final Answer:")[-1].strip()
                chain.confidence = 0.9
                break

        return chain

    # General execution interface
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute reasoning module operation."""
        operations = {
            # Chain of Thought
            "reason": self.reason,
            "reason_tree": self.reason_tree,
            "self_consistency_check": self.self_consistency_check,

            # Planning
            "create_plan": self.create_plan,
            "execute_plan": self.execute_plan,
            "plan_and_execute": self.plan_and_execute,

            # Verification
            "verify": self.verify,
            "critique": self.critique,

            # Decision Making
            "decide": self.decide,
            "analyze_options": self.analyze_options,

            # Math Reasoning
            "solve_math": self.solve_math,

            # Logic Reasoning
            "logic_prove": self.logic_prove,
            "logic_verify": self.logic_verify,

            # ReAct
            "react": self.react,
        }
        if operation in operations:
            return await operations[operation](**kwargs)
        raise NotImplementedError(f"Operation '{operation}' not supported")


# Mock backend implementations
class MockChainOfThoughtBackend(ChainOfThoughtBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_cot"}

    async def reason(self, problem: str, context: Optional[str] = None, examples: Optional[List[Dict[str, str]]] = None, max_steps: int = 10, **kwargs) -> ReasoningChain:
        import random
        steps = [
            ReasoningStep(step_number=1, description="Understand the problem", reasoning=f"Analyzing: {problem}", conclusion="Problem understood"),
            ReasoningStep(step_number=2, description="Plan approach", reasoning="Breaking down into steps", conclusion="Approach planned"),
            ReasoningStep(step_number=3, description="Execute reasoning", reasoning="Working through logic", conclusion="Solution found"),
        ]
        return ReasoningChain(problem=problem, steps=steps, final_answer="Mock answer", confidence=0.85, method=ReasoningMethod.CHAIN_OF_THOUGHT)

    async def reason_step_by_step(self, problem: str, **kwargs) -> ReasoningChain:
        return await self.reason(problem, **kwargs)


class MockTreeOfThoughtsBackend(TreeOfThoughtsBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_tot"}

    async def reason(self, problem: str, branching_factor: int = 3, max_depth: int = 5, pruning_threshold: float = 0.3, **kwargs) -> ReasoningTree:
        root = ReasoningStep(step_number=0, description="Root", reasoning=problem)
        nodes = {"root": root}
        edges = {"root": ["child_1", "child_2", "child_3"]}
        for i in range(1, 4):
            nodes[f"child_{i}"] = ReasoningStep(step_number=i, description=f"Branch {i}", reasoning=f"Exploring path {i}")
        return ReasoningTree(problem=problem, root=root, nodes=nodes, edges=edges, best_path=["root", "child_1"], method=ReasoningMethod.TREE_OF_THOUGHTS)


class MockPlanningBackend(PlanningBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_planning"}

    async def create_plan(self, goal: str, context: Optional[str] = None, constraints: Optional[List[str]] = None, available_actions: Optional[List[str]] = None, **kwargs) -> Plan:
        steps = [
            {"step": 1, "action": "analyze", "description": f"Analyze goal: {goal}"},
            {"step": 2, "action": "plan", "description": "Create subgoals"},
            {"step": 3, "action": "execute", "description": "Execute plan"},
            {"step": 4, "action": "verify", "description": "Verify results"},
        ]
        return Plan(goal=goal, steps=steps, method=PlanningMethod.LLM_PLANNING)

    async def execute_plan(self, plan: Plan, executor: Any, **kwargs) -> ExecutionResult:
        return ExecutionResult(plan_id=plan.plan_id, success=True, final_output="Plan executed successfully")

    async def replan(self, plan: Plan, execution_result: ExecutionResult, **kwargs) -> Plan:
        return Plan(goal=plan.goal, steps=plan.steps, method=PlanningMethod.LLM_PLANNING)


class MockVerificationBackend(VerificationBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_verification"}

    async def verify(self, claim: str, evidence: Optional[List[str]] = None, context: Optional[str] = None, **kwargs) -> VerificationResult:
        return VerificationResult(target=claim, passed=True, score=0.9, reasoning="Verified based on evidence")

    async def critique(self, solution: str, problem: str, criteria: Optional[List[str]] = None, **kwargs) -> VerificationResult:
        return VerificationResult(target=solution, passed=True, score=0.85, issues=[], suggestions=["Consider edge cases"], reasoning="Solution is mostly correct")


class MockDecisionBackend(DecisionBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_decision"}

    async def decide(self, problem: str, options: List[DecisionOption], criteria: Optional[List[str]] = None, context: Optional[str] = None, **kwargs) -> DecisionResult:
        import random
        for opt in options:
            opt.score = random.random()
        chosen = max(options, key=lambda o: o.score)
        return DecisionResult(problem=problem, options=options, chosen_option=chosen, reasoning=f"Selected {chosen.name} with highest score", confidence=chosen.score)


class MockMathReasoningBackend(MathReasoningBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_math"}

    async def solve(self, problem: str, method: Optional[ReasoningMethod] = None, show_work: bool = True, **kwargs) -> ReasoningChain:
        steps = [
            ReasoningStep(step_number=1, description="Parse problem", reasoning=f"Problem: {problem}"),
            ReasoningStep(step_number=2, description="Identify method", reasoning="Using algebraic manipulation"),
            ReasoningStep(step_number=3, description="Solve", reasoning="Step by step calculation"),
            ReasoningStep(step_number=4, description="Verify", reasoning="Checking answer"),
        ]
        return ReasoningChain(problem=problem, steps=steps, final_answer="42", confidence=0.9, method=method or ReasoningMethod.CHAIN_OF_THOUGHT)


class MockLogicReasoningBackend(LogicReasoningBackend):
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    async def cleanup(self) -> None:
        pass
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "backend": "mock_logic"}

    async def solve(self, premises: List[str], conclusion: str, **kwargs) -> VerificationResult:
        return VerificationResult(target=conclusion, passed=True, score=0.95, reasoning="Conclusion follows from premises")

    async def prove(self, theorem: str, axioms: List[str], **kwargs) -> ReasoningChain:
        steps = [
            ReasoningStep(step_number=1, description="State theorem", reasoning=f"Theorem: {theorem}"),
            ReasoningStep(step_number=2, description="Apply axioms", reasoning="Using given axioms"),
            ReasoningStep(step_number=3, description="Derive proof", reasoning="Logical deduction steps"),
        ]
        return ReasoningChain(problem=theorem, steps=steps, final_answer="Proven", confidence=0.95, method=ReasoningMethod.LOGICAL)


__all__ = [
    "ReasoningModule",
    "ReasoningType",
    "ReasoningMethod",
    "PlanningMethod",
    "ProblemType",
    "ReasoningStep",
    "ReasoningChain",
    "ReasoningTree",
    "Plan",
    "ExecutionResult",
    "DecisionOption",
    "DecisionResult",
    "VerificationResult",
    "ReasoningBackend",
    "ChainOfThoughtBackend",
    "TreeOfThoughtsBackend",
    "PlanningBackend",
    "VerificationBackend",
    "DecisionBackend",
    "MathReasoningBackend",
    "LogicReasoningBackend",
]