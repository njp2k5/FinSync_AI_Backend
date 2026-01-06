from langgraph.graph import StateGraph
from app.graph.state import LoanGraphState

from app.agents_langraph.sales_agent import sales_agent
from app.agents_langraph.risk_agent import risk_agent
from app.agents_langraph.compliance_agent import compliance_agent
from app.agents_langraph.confidence_agent import confidence_agent
from app.agents_langraph.orchestrator_agent import orchestrator_agent

def build_loan_graph():
    graph = StateGraph(LoanGraphState)

    graph.add_node("sales", sales_agent)
    graph.add_node("risk", risk_agent)
    graph.add_node("compliance", compliance_agent)
    graph.add_node("confidence", confidence_agent)
    graph.add_node("orchestrator", orchestrator_agent)

    graph.set_entry_point("sales")

    graph.add_edge("sales", "risk")           # parallelizable later
    graph.add_edge("risk", "compliance")      # hard gate
    graph.add_edge("compliance", "confidence")
    graph.add_edge("confidence", "orchestrator")

    return graph.compile()
