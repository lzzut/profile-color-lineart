# 彩色线稿工作流 AI 接入

`ProfileLineart_Color_Lineart_v4_3` 接收一张已经画好的二次元图，输出一张黑底彩色线稿 PNG。人物、角度、表情、纹身和刻字来自底图。默认的 `edges` 可在 CPU 运行，无需下载模型。[界面模板](workflows/ProfileLineart_Color_Lineart_v4_3.json) · [API 模板](workflows/ProfileLineart_Color_Lineart_v4_3.api.json)

已有底图时，给出主线的暗色和亮色，以及两处可选记号的区域、取样色和成品色。色值用 `#RRGGBB`，以用户选定的颜色优先。能查看底图时可估计区域和取样色。请用户看 **125／135** 确认两处记号轮廓。

需要准备新底图时，提示词用于独立绘画工作流。写清角色特征、朝向、表情和记号位置。严格侧脸可用 `strict left-facing side profile, nose pointing left, one visible eye`，然后用成图作为线稿工作流的输入。[绘画提示词示例](GUIDE_COLOR_LINEART.md#需要新底图时怎样写提示词)

| 用途 | 节点与字段 | 参数 |
| --- | --- | --- |
| 输入 | `5.inputs.image` | ComfyUI `input` 内的文件名，可含子目录 |
| 提线 | `20.inputs.method`、`detail`、`contrast_recovery` | 默认 `edges`、`0.50`、`true` |
| 主线颜色 | `90.inputs.color`、`91.inputs.color` | 暗部和亮部各填一个色值 |
| 记号 A | `121.inputs` 的 `mode`、`region`、`color_mode`、`color_tolerance` | **96** 为底图取样色，**97** 为自定义轮廓色 |
| 记号 B | `131.inputs` 的相同字段 | **98** 为底图取样色，**99** 为自定义轮廓色 |
| 输出 | `29`、`136`、`125`、`135`、`28` | 白线预览、提线状态、A/B 轮廓预览、成品 |

`mode=off` 关闭记号。用 `skin_color` 选肤色区域内的高饱和彩色记号，`region_color` 选矩形内相近的高饱和颜色，`region_sample` 选矩形内接近取样色的像素，适合灰色、浅金等记号。黑字可用 `region_dark`，白字可用 `region_light`。设 `color_mode=original` 保留原色，设 `custom` 时使用该组的自定义颜色。取样容差默认 `12`。在预览里出现漏选或背景串色时，再微调容差和范围。

`region` 为逗号分隔的四个数字，顺序为左、上、右、下。坐标按节点 20 缩放并补边后的画布归一化到 0–1。左小于右，上小于下。

## 运行浅色刻字例子

在已按 README 安装并启动的 ComfyUI 上运行。设置 JSON 以节点编号为键，第二层是模板的参数名。未列出的参数沿用模板。示例会给灰色 `A7` 和浅金色 `03` 保留各自的原色轮廓。[设置 JSON](examples/profile_lineart_pale_settings.json) · [练习底图](examples/profile_lineart_pale_marks.png)

```powershell
python -X utf8 .\lineart_api.py --settings .\examples\profile_lineart_pale_settings.json --out pale_result.png
```

自己的二次元底图可传 `--image 路径`，脚本会上传图片。ComfyUI 地址默认为 `http://127.0.0.1:8188`，可通过 `--url` 修改。

## 直接调用 API

1. 通过 `POST /upload/image` 上传二次元底图，使用 multipart 表单的 `image` 字段。把返回的 `name` 或 `subfolder/name` 填入节点 5。
2. 用同一组设置更新 API 图的 `inputs` 和界面图的 `widgets_values`、`widgets_values_named`。辅助函数 `set_inputs` 提供了示例。[脚本](lineart_api.py)
3. 把更新后的 API 图作为 `prompt` 提交到 `POST /prompt`。在 `extra_data.extra_pnginfo.workflow` 带上界面图并保留其 `id` 和 `workflow_name`，这样成品 PNG 可恢复本次的参数。
4. 用 `GET /history/{prompt_id}` 获取结果。成功时读取 `outputs["28"]["images"]`。图像条目中的 `subfolder` 和 `filename` 给出成品位置。提线失败时可把工作流返回的具体原因告诉用户，再一起选底图或调参数。
