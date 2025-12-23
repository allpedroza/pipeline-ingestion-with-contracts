"""
Data Contract Agents Module

This module provides intelligent agents for creating and managing data contracts
through interactive conversations, abstracting technical complexity.

Available agents:
- ContractCreatorAgent: Rule-based agent with guided questions
- InteractiveContractSession: Terminal UI for rule-based agent
- LLMContractAgent: AI-powered agent using Claude (requires 'anthropic' package)
- LLMContractSession: Terminal UI for AI-powered agent
"""

from .contract_creator import ContractCreatorAgent
from .interactive_session import InteractiveContractSession

__all__ = [
    "ContractCreatorAgent",
    "InteractiveContractSession",
]

# Lazy imports for LLM components (optional dependency)
try:
    from .llm_agent import LLMContractAgent, LLMConfig
    from .llm_session import LLMContractSession

    __all__.extend([
        "LLMContractAgent",
        "LLMConfig",
        "LLMContractSession",
    ])
except ImportError:
    # anthropic not installed, LLM features unavailable
    pass
