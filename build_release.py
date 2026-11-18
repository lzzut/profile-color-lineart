"""Build the v4.3 preview ZIP from the public files in this workspace."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from prepare_image_workflow import NODE_FILES, PALE_SAMPLE, PLUGIN, ROOT, SAMPLE, WORKFLOW_NAME


PUBLIC_FILES = (
    ".gitignore", "README.md", "GUIDE_COLOR_LINEART.md", "AI_INTEGRATION.md", "requirements.txt",
    "prepare_image_workflow.py", "lineart_api.py", "build_release.py",
    f"workflows/{WORKFLOW_NAME}.json", f"workflows/{WORKFLOW_NAME}.api.json",
    *(PLUGIN / name for name in NODE_FILES),
    f"examples/{SAMPLE}", f"examples/{PALE_SAMPLE}", "examples/profile_lineart_pale_settings.json",
    "examples/profile_lineart_pale_result.png",
    "tests/test_lineart_release.py",
)


if __name__ == "__main__":
    output = ROOT / "dist/profile-color-lineart-v4.3-preview.zip"
    for relative in PUBLIC_FILES:
        if not (ROOT / relative).is_file():
            raise FileNotFoundError(f"Missing release file: {relative}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for relative in PUBLIC_FILES:
            archive.write(ROOT / relative, Path(relative).as_posix())
    print(output)
