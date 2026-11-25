from typing import List

from app.services.vector_store import RetrievedNode

BASELINE_A_SYSTEM_PROMPT = (
    "You are AdaptiveDocAI, an accurate document question-answering assistant. "
    "Answer the user's question using ONLY the provided document evidence passages. "
    "Always include page-level citations in the format [Source: <document_name>, Page <page_number>]. "
    "If the provided passages do not contain enough information, clearly state that the answer "
    "is not found in the retrieved passages."
)


def build_rag_user_prompt(query: str, nodes: List[RetrievedNode]) -> str:
    """Format retrieved passages with document name and page provenance for LLM grounding."""
    if not nodes:
        return f"No evidence passages were retrieved.\n\nQuestion: {query}\nAnswer:"

    blocks = []
    for idx, node in enumerate(nodes, start=1):
        blocks.append(
            f"[Evidence {idx} | {node.document_name} | Page {node.page_number}]\n{node.content}"
        )
    context_str = "\n\n".join(blocks)
    return f"Retrieved Evidence:\n\n{context_str}\n\nQuestion: {query}\nAnswer:"

