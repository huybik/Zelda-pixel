import ast
import os
from graphviz import Digraph


class FunctionCallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.calls = []
        self.current_function = None
        self.defined_functions = set()
        self.class_functions = {}
        self.current_class = None

    def visit_ClassDef(self, node):
        previous_class = self.current_class
        self.current_class = node.name
        self.class_functions[node.name] = set()
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.class_functions[node.name].add(item.name)
        self.generic_visit(node)
        self.current_class = previous_class

    def visit_FunctionDef(self, node):
        self.defined_functions.add(node.name)
        previous_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = previous_function

    def visit_Call(self, node):
        if self.current_function:
            # Handle direct function calls
            if isinstance(node.func, ast.Name):
                self.calls.append((self.current_function, node.func.id))
            # Handle method calls
            elif isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    self.calls.append(
                        (
                            self.current_function,
                            f"{node.func.value.id}.{node.func.attr}",
                        )
                    )
        self.generic_visit(node)


def analyze_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        try:
            tree = ast.parse(file.read())
            visitor = FunctionCallVisitor()
            visitor.visit(tree)
            return visitor.calls, visitor.defined_functions, visitor.class_functions
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return [], set(), {}


def generate_call_graph(directory):
    dot = Digraph(comment="Function Call Graph")
    dot.attr(rankdir="LR")

    all_calls = []
    all_defined_functions = set()
    all_class_functions = {}

    # Analyze Python files
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file != "callgraph.py":
                file_path = os.path.join(root, file)
                calls, defined_functions, class_functions = analyze_file(file_path)
                all_calls.extend(calls)
                all_defined_functions.update(defined_functions)
                all_class_functions.update(class_functions)

    # Add nodes for all defined functions
    for func in all_defined_functions:
        dot.node(func, func)

    # Add edges for function calls
    added_edges = set()
    for caller, callee in all_calls:
        if caller and callee:
            edge = (caller, callee)
            if edge not in added_edges:
                dot.edge(caller, callee)
                added_edges.add(edge)

    # Save the graph
    try:
        dot.render("function_call_graph", format="png", cleanup=True)
        print("Call graph generated as 'function_call_graph.png'")
    except Exception as e:
        print(f"Error generating graph: {e}")


if __name__ == "__main__":
    # Generate call graph for the current directory
    generate_call_graph(".")
