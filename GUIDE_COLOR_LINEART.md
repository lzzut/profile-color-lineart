# 彩色线稿配色和提示词指南

## 不借助 AI 准备底图

选一张已有的二次元插画。需要严格侧脸时，就选一张鼻尖朝向画面一侧、只露出一只眼的底图。需要正脸、微笑或惊讶，就直接选对应表情的插画。背景简单、头发和背景有明暗差、记号所在部位完整入镜，更容易提取出清楚的轮廓。

要加一段准确的刻字，可以用 Windows 画图打开底图，选文字工具「A」，在相应位置打字，再另存为 PNG。亮处放深色字，暗处放浅色字。也可以直接用安装时自带的练习图跟做。[双刻字练习底图](examples/profile_lineart_practice.png)

## 有图片时直接出线稿

在 ComfyUI 的「工作流」列表打开 `ProfileLineart_Color_Lineart_v4_3`。到「上传二次元底图」选择插画，点「运行」。默认的 `edges` 使用 OpenCV 在本机找轮廓，CPU 就能处理。正脸、侧脸和表情沿用输入图。PNG、JPEG、WebP 等由 ComfyUI 的图片节点读取，透明区域按白底处理。

先看节点 **29** 的白线预览。细节太多就在 **20** 把 `detail` 从 `0.50` 降到 `0.30`。丢了细线就试 `0.65`。默认开启的 `contrast_recovery` 会在白线接近空白时试一次反差增强。提线状态会显示是否用了增强。若提示「几乎没有检测到线条」，可以提高 `detail` 或换一张反差更大的底图。

用下面的色值给主线或记号上色，再点一次「运行」。到 ComfyUI 的 `output/profile_lineart/color_lineart_v4_3/` 查看 `final_*.png`。

## 给主线选暗色和亮色

先从角色最醒目的颜色里选一个色相，比如初音头发的蓝绿。用同一色系的深色和浅色拉开明暗。在黑底上看成品，暗处线条需要能认出轮廓。记号只占很小的面积时，可以选一个冷暖不同的强调色，比如蓝绿主线配暖红或金色。点 **90** 和 **91** 的色块，可以直接输入十六进制色值。

| 想要的效果 | 90 主线暗部色 | 91 主线亮部色 | 记号用色举例 |
| --- | --- | --- | --- |
| 初音蓝绿 | `#087B80` | `#9CFFF0` | 红色 01 沿用原色，或换成金色 `#FFCB6B` |
| 悟饭黄绿 | `#4D7613` | `#FAFF9A` | 用淡紫 `#BE9AFF` 区分刻字 |
| 橙红暖光 | `#A91C06` | `#FFBD69` | 用冰蓝 `#65E3FF` 给小记号提亮 |

主线颜色合适但明暗差太小，可以在 **120** 把 `shadow_level` 从 `0.55` 降到 `0.40`，或把 `tone_contrast` 从 `1.60` 加到 `1.90`。一次只改一项，再用同一张图比较。想让蓝绿高光饱和一点，可以把 **91** 换成 `#28D3BD`，把 **120** 的 `highlight_level` 调到 `0.85`。觉得光晕太厚就在 **122** 将 `glow_strength` 从 `0.45` 调到 `0.25`。

## 给纹身和刻字分别上色

画布下方的「记号 A」和「记号 B」可以分别设定。A 用 **121** 选区域、**96** 选原图上的颜色、**97** 选输出色。B 对应 **131／98／99**。记号默认关闭，使用哪一处就开哪一组。两组适合选不同区域。

| 底图上的记号 | 在 A 或 B 选的 `mode` | 怎样指定位置和颜色 |
| --- | --- | --- |
| 肤色区域里的红色 01 | `skin_color` | 底图色块选红色，例如 `#EF003E` |
| 彩色印记或刺青 | `region_color` | 设矩形范围，底图色块选原图印记的颜色 |
| 灰色、浅金色等淡色记号 | `region_sample` | 设矩形范围，在底图色块填入记号笔画中央的颜色 |
| 亮底上的黑字或深色刻痕 | `region_dark` | 把矩形收在文字周围 |
| 深底上的白字或银白刻字 | `region_light` | 把矩形收在文字周围 |

`region` 的四个数字分别是左、上、右、下。以白线预览的整张画布为准，左上角是 `0,0`，右下角是 `1,1`。横向位置除以画布宽，纵向位置除以画布高。比如 `0.63,0.60,0.78,0.70` 选的是画布右下方一小块。若选进衣服或背景，先缩小区域。在 A 的 **125** 或 B 的 **135** 看轮廓预览。

`color_mode=original` 沿用底图的颜色。设为 `custom` 后，A 用 **97**、B 用 **99** 的色块。比如把初音红色 01 改成金色，在 A 选 `skin_color`，**96** 填 `#EF003E` 定位红字，`color_mode` 选 `custom`，**97** 填 `#FFCB6B`。宽笔画只保留边沿，细笔画保留为细线，轮廓会做抗锯齿。默认 `outline_width=1.5`，想让宽字留更多黑底可以试 `1.0`。深色记号用 `original` 时，`dark_floor` 可提高最暗笔画的可见度。

用随包练习图可以直接照填下面的设置。任选一张底图，两组记号各用表中对应的一行。主线用默认橙红，节点 **20** 保持 `edges` 和 `detail=0.50`。

| 底图 | 记号 | 模式 | `region` | 颜色 |
| --- | --- | --- | --- | --- |
| `profile_lineart_practice.png` | A 的黑色 A7 | `region_dark` | `0.13,0.35,0.42,0.63` | `custom`，**97** 填 `#65E3FF` |
| 同上 | B 的白色 03 | `region_light` | `0.59,0.35,0.87,0.63` | `custom`，**99** 填 `#BE9AFF` |
| `profile_lineart_pale_marks.png` | A 的灰色 A7 | `region_sample` | `0.13,0.35,0.42,0.63` | `original`，**96** 填 `#989898` |
| 同上 | B 的浅金色 03 | `region_sample` | `0.59,0.35,0.87,0.63` | `original`，**98** 填 `#DACB9C` |

用 `region_sample` 时，`color_tolerance` 先用 **12**。预览漏掉笔画时加到 **16**。把背景或皮肤一并选进来时缩小区域，或把容差降到 **8**。[浅色刻字练习图](examples/profile_lineart_pale_marks.png)

## 需要新底图时怎样写提示词

提示词用在独立绘画工作流。按「人物和辨识点 → 视角 → 构图和表情 → 线条和背景 → 记号位置和原色」写。侧脸要把方向、鼻尖朝向和只露出一只眼说清楚。构图要把记号所在部位包括进来。用平涂、清楚的色块和简单背景，能方便后续提线。

以初音左侧脸为例，可把这两段分别交给绘画模型的正向和负向提示词。线稿还可以使用其他模型生成的图片。

**正向**

```text
Hatsune Miku, teal twin tails, strict left-facing side profile, nose pointing left,
one visible eye, head and shoulders, gentle smile, visible upper arm,
clean anime outlines, flat cel shading, plain light gray background,
one small red "01" tattoo on the visible upper arm
```

**负向**

```text
front view, three-quarter view, both eyes visible, cropped upper arm,
busy background, blurry edges, extra tattoos, duplicate lettering
```

想要正脸，把视角改成 `front view, looking at the viewer, both eyes visible`，并从负向去掉 `front view` 和 `both eyes visible`。想要大笑，把 `gentle smile` 换成 `laughing, open mouth`。如果具体刻字必须一字不差，可以先用画图的文字工具把字放到彩色底图上，选明暗对比明显的文字，然后交给同一个线稿工作流。

也可以请 AI 建议配色，再把你选中的色值填入色块。例如「蓝绿头发的角色，黑底，手臂有红色 01。给我一深一浅两种蓝绿主线色，以及一种能和蓝绿分开的记号色。请给三个十六进制色值。」已有图片和想用的颜色时，上传并填色即可。

需要 AI 根据底图给出节点设置，或通过本地 ComfyUI API 运行时，可把接入说明连同底图交给 AI。[AI 接入说明](AI_INTEGRATION.md)
