from app.schemas.research import ChatRequest
from app.services.assistant import answer
from app.services.workspace import WorkspaceStore


def test_workspace_returns_matching_document_excerpt():
    store = WorkspaceStore()
    store.add_document("report.txt", "Revenue margin improved because operating costs declined significantly.", "RELIANCE")
    matches = store.search_documents("Why did margin improve?", "RELIANCE")
    assert matches[0]["document"] == "report.txt"


def test_assistant_refuses_buy_sell_advice():
    response = answer(ChatRequest(message="Should I buy RELIANCE?"))
    assert "cannot tell you what to buy or sell" in response["answer"]
