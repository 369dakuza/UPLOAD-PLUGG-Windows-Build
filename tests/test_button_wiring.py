import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_FILES = (
    PROJECT_ROOT / "src" / "upload_plugg" / "ui" / "pages.py",
    PROJECT_ROOT / "src" / "upload_plugg" / "ui" / "main_window.py",
)


def expression_key(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = expression_key(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


class ButtonWiringTests(unittest.TestCase):
    def test_every_named_push_button_has_a_clicked_connection(self):
        missing: list[str] = []
        for path in UI_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
                buttons: set[str] = set()
                connected: set[str] = set()
                for node in ast.walk(function):
                    if isinstance(node, (ast.Assign, ast.AnnAssign)):
                        value = node.value
                        if (
                            isinstance(value, ast.Call)
                            and expression_key(value.func) == "QPushButton"
                        ):
                            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                            buttons.update(filter(None, (expression_key(target) for target in targets)))
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "connect"
                        and isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "clicked"
                    ):
                        key = expression_key(node.func.value.value)
                        if key:
                            connected.add(key)
                for button in sorted(buttons - connected):
                    missing.append(f"{path.name}:{function.name}:{button}")

        self.assertEqual(missing, [], f"Buttons without clicked handlers: {missing}")

    def test_combo_box_popups_use_dark_readable_colors(self):
        theme = (PROJECT_ROOT / "src" / "upload_plugg" / "ui" / "theme.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("QComboBox QAbstractItemView", theme)
        self.assertIn("background-color: #080a0d", theme)
        self.assertIn("color: #ffffff", theme)


if __name__ == "__main__":
    unittest.main()
