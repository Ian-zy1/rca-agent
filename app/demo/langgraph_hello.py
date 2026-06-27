from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class HelloState(TypedDict):
    message: str


def node_a(state: HelloState) -> dict:
    return {"message": state["message"] + "-> 节点A处理"}


def node_b(state: HelloState) -> dict:
    return {"message": state["message"] + "-> 节点B处理"}


graph = StateGraph(HelloState)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge(START, "a")
graph.add_edge("a", "b")
graph.add_edge("b", END)

app_graph = graph.compile()

if __name__ == "__main__":
    result = app_graph.invoke({"message": "hello"})
    print(result)
