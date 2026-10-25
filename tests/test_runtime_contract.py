"""Every shipped Python function has a fully annotated signature.

Discover runtime modules recursively and inspect all functions, including nested
functions and methods. Only implicit first self/cls method receivers may omit
annotations; return values and every other parameter must be annotated.
"""

import ast
from pathlib import Path


def signature_gaps(tree: ast.AST, path: str) -> list[str]:
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    gaps: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        location = f"{path}:{node.lineno}: {node.name}"
        if node.returns is None:
            gaps.append(f"{location}: missing return annotation")
        positional = [*node.args.posonlyargs, *node.args.args]
        receiver = None
        static = any(
            (isinstance(decorator, ast.Name) and decorator.id == "staticmethod")
            or (isinstance(decorator, ast.Attribute) and decorator.attr == "staticmethod")
            for decorator in node.decorator_list
        )
        if (
            isinstance(parents.get(node), ast.ClassDef)
            and not static
            and positional
            and positional[0].arg in {"self", "cls"}
        ):
            receiver = positional[0]
        parameters = [*positional, *node.args.kwonlyargs]
        if node.args.vararg is not None:
            parameters.append(node.args.vararg)
        if node.args.kwarg is not None:
            parameters.append(node.args.kwarg)
        for parameter in parameters:
            if parameter is not receiver and parameter.annotation is None:
                gaps.append(f"{location}: missing annotation for parameter {parameter.arg!r}")
    return gaps


def test_runtime_signatures_are_annotated() -> None:
    root = Path(__file__).resolve().parents[1]
    sources = sorted((root / "src/planzilla").rglob("*.py"))
    assert sources, "No runtime Python sources discovered"
    gaps = [
        gap
        for source in sources
        for gap in signature_gaps(
            ast.parse(source.read_text(encoding="utf-8")), source.relative_to(root).as_posix()
        )
    ]
    assert not gaps, "Runtime signature annotations missing:\n" + "\n".join(gaps)
