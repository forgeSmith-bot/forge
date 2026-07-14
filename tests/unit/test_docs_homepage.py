import os
import re


def test_docs_homepage_structure_and_links() -> None:
    """Verify the docs/index.md structure, content, and the presence of critical workflow links."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    index_path = os.path.join(base_dir, "docs", "index.md")
    assert os.path.exists(index_path), f"docs/index.md does not exist at {index_path}"

    with open(index_path, encoding="utf-8") as f:
        content = f.read()

    # Verify each workflow is mentioned with its specific emoji and header structure
    assert "### 🚀 Feature Workflow" in content, "Feature Workflow section missing"
    assert "### 🐛 Bug Workflow" in content, "Bug Workflow section missing"
    assert "### 🛠️ Task Workflow" in content, "Task Workflow section missing"

    # Verify that the correct guide links are present in the Supported Workflows description
    assert "guide/feature-workflow.md" in content, "Link to guide/feature-workflow.md is missing"
    assert "guide/bug-workflow.md" in content, "Link to guide/bug-workflow.md is missing"
    assert "guide/task-workflow.md" in content, "Link to guide/task-workflow.md is missing"
    assert "getting-started.md" in content, "Getting started link is missing"

    # Verify all references exist on filesystem
    links = re.findall(r"\]\(([^)]+)\)", content)
    for link in links:
        # Ignore external links if any, only check local relative markdown files
        if not link.startswith("http") and link.endswith(".md"):
            # Clean anchors
            link_clean = link.split("#")[0]
            target_path = os.path.join(base_dir, "docs", link_clean)
            assert os.path.exists(target_path), f"Linked file does not exist: {target_path}"
