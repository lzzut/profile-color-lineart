"""Run the v4.3 workflow through the local ComfyUI API."""

import argparse
import json
import time
from pathlib import Path

import requests

from prepare_image_workflow import ROOT, WORKFLOW_NAME


DEFAULT_URL = "http://127.0.0.1:8188"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def set_inputs(graph, workflow, settings):
    for node_id, fields in settings.items():
        if node_id not in graph or not isinstance(fields, dict):
            raise ValueError(f"无效的节点设置 {node_id}")
        node = next(item for item in workflow["nodes"] if str(item["id"]) == node_id)
        named = node["widgets_values_named"]
        inputs = graph[node_id]["inputs"]
        for field, value in fields.items():
            if field not in named or field not in inputs or isinstance(value, (list, dict)):
                raise ValueError(f"{node_id}.{field} 不是模板中可修改的参数")
            inputs[field] = value
            node["widgets_values"][list(named).index(field)] = value
            named[field] = value


def submit(url, settings=None, image=None):
    path = ROOT / "workflows" / WORKFLOW_NAME
    graph = read_json(path.with_suffix(".api.json"))
    workflow = read_json(path.with_suffix(".json"))
    set_inputs(graph, workflow, settings or {})
    if image is not None:
        with image.open("rb") as file:
            response = requests.post(url + "/upload/image", files={"image": (image.name, file)},
                                     data={"type": "input", "subfolder": "profile_lineart"}, timeout=30)
        response.raise_for_status()
        item = response.json()
        name = "/".join(filter(None, (item.get("subfolder"), item["name"])))
        set_inputs(graph, workflow, {"5": {"image": name}})
    response = requests.post(url + "/prompt", json={
        "prompt": graph,
        "extra_data": {"extra_pnginfo": {"workflow": workflow}},
    }, timeout=30)
    if not response.ok:
        raise RuntimeError(f"ComfyUI 拒绝任务（{response.status_code}）\n{response.text}")
    return response.json()["prompt_id"]


def wait_for_result(url, prompt_id, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = requests.get(f"{url}/history/{prompt_id}", timeout=10)
        response.raise_for_status()
        if record := response.json().get(prompt_id):
            status = record["status"]
            if status["status_str"] != "success":
                for kind, details in status.get("messages", []):
                    if kind == "execution_error":
                        raise RuntimeError(details.get("exception_message", "ComfyUI 运行失败。"))
                raise RuntimeError(f"ComfyUI 运行结束，状态为 {status['status_str']}")
            return record
        time.sleep(0.2)
    raise TimeoutError(f"等待任务 {prompt_id} 超时")


def view_image(url, item):
    response = requests.get(url + "/view", params=item, timeout=30)
    response.raise_for_status()
    return response.content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="本机 ComfyUI 地址")
    parser.add_argument("--image", type=Path, help="要上传的二次元底图。省略时使用工作流或设置中的图片")
    parser.add_argument("--settings", type=Path, help="节点设置 JSON")
    parser.add_argument("--out", type=Path, help="将成品另存到本地文件")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    try:
        settings = read_json(args.settings) if args.settings else None
        prompt_id = submit(url, settings, args.image)
        result = wait_for_result(url, prompt_id)
        item = result["outputs"]["28"]["images"][0]
        if args.out:
            args.out.write_bytes(view_image(url, item))
    except (OSError, ValueError, RuntimeError, requests.RequestException) as exc:
        parser.exit(1, f"{exc}\n")
    print("/".join(filter(None, (item["subfolder"], item["filename"]))))


if __name__ == "__main__":
    main()
