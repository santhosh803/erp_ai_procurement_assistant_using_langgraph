"""Tunable constants and prompt templates for the procurement graph."""

# Validator thresholds
CONFIDENCE_THRESHOLD = 0.25
MAX_RETRIEVAL_ATTEMPTS = 2

# Retrieval
DEFAULT_K = 4
RETRY_K = 8

# Memory
MEMORY_WINDOW = 4   # turns kept in rolling summary

# Recursion safety net for the validator retry loop
GRAPH_RECURSION_LIMIT = 10

# Synonym expansion used on a retry retrieval pass
SYNONYM_MAP = {
    "PR": "purchase requisition",
    "PO": "purchase order",
    "GR": "goods receipt",
    "IR": "invoice receipt",
    "RFQ": "request for quotation",
    "P2P": "procure to pay",
    "SOP": "standard operating procedure",
    "GR/IR": "goods receipt invoice receipt account",
}

# Used by the LLM-based classifier node. Asks Qwen to emit ONE label.
CLASSIFIER_TEMPLATE = """You are a query classifier for a SAP S/4HANA procurement assistant.
Classify the user's question into exactly ONE of these categories:

- FACTUAL: definitions, lookups, "what is", "explain", concept questions
- WORKFLOW: process/step questions ("how do I", "what are the steps", "process for", multi-stage flows)
- CHAT: greetings, small talk, meta questions about the assistant itself

Conversation summary (may be empty):
{summary}

User question: {query}

Respond with EXACTLY one word: FACTUAL, WORKFLOW, or CHAT."""

# Patterns the tool_caller looks for
ID_PATTERN = r"\b(PO|PR)[-\s]?\d{4,}\b"
STEP_INTENT_PATTERN = r"how many steps|count.*steps|number of steps|how many stages"
