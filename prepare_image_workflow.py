"""Install the v4.3 illustration workflow into an existing ComfyUI."""

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOW_NAME = "ProfileLineart_Color_Lineart_v4_3"
SAMPLE = "profile_lineart_practice.png"
PALE_SAMPLE = "profile_lineart_pale_marks.png"
PLUGIN = Path("custom_nodes/profile_lineart_style")
NODE_FILES = ("__init__.py", "image_input.py")


def install_workflow(comfy_dir, base_directory=None):
    comfy_dir = comfy_dir.resolve()
    if not (comfy_dir / "main.py").is_file():
        raise FileNotFoundError(f"请选择含有 main.py 的 ComfyUI 程序目录。当前路径为 {comfy_dir}")
    base = base_directory.resolve() if base_directory else comfy_dir
    workflow = Path(f"workflows/{WORKFLOW_NAME}.json")
    files = [(PLUGIN / name, PLUGIN / name, True) for name in NODE_FILES]
    files.append((workflow, Path("user/default") / workflow, False))
    for name in (SAMPLE, PALE_SAMPLE):
        files.append((Path("examples") / name, Path("input") / name, False))
    for source, _, _ in files:
        if not (ROOT / source).is_file():
            raise FileNotFoundError(f"安装包不完整，缺少 {source}")
    for source, relative, replace in files:
        destination = base / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if replace or not destination.exists():
            shutil.copy2(ROOT / source, destination)
    return base / "user/default" / workflow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfy-dir", type=Path, required=True, help="包含 main.py 的 ComfyUI 程序目录")
    parser.add_argument("--base-directory", type=Path, help="ComfyUI 另设的 base directory")
    args = parser.parse_args()
    try:
        path = install_workflow(args.comfy_dir, args.base_directory)
    except OSError as exc:
        parser.exit(1, f"{exc}\n")
    print(f"已安装工作流 {path}")


if __name__ == "__main__":
    main()
