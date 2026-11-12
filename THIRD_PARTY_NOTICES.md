# 来源、署名与许可范围

本仓库同时包含应用代码、研究标注数据、衍生模型和教学建模脚本。根目录的 [MIT License](LICENSE) 适用于 Mouse Atlas 贡献者新增的应用代码与配套说明；下载或分发其他材料时请使用下表对应的许可。

| 材料 | 署名与许可 | 附带的原始说明 |
| --- | --- | --- |
| Digimouse 标注体，包括 [atlas.zip](scripts/voxel/atlas.zip) | Belma Dogdas、David Stout、Arion F. Chatziioannou、Richard M. Leahy；CC BY-SA 4.0 | 压缩包内含 `atlas/LICENSE.txt`；亦见 [Digimouse 许可](https://neuroimage.usc.edu/neuro/Digimouse_license)。 |
| [Digimouse 表面及元数据](public/models/digimouse-voxel)，包括内脏、脑区、骨骼、体表和由这些表面导出的单结构模型 | 原始作者同上；Mouse Atlas 负责从标注体素提取表面，添加名称和展示配色，拆分六组成对结构。派生模型延续 CC BY-SA 4.0。 | [完整作者、重建方法、修改和许可说明](public/models/digimouse-voxel/ATTRIBUTION.txt) |
| [教学补建资产](public/models/mouse-teaching)：消化道、气道与泌尿管道、区域动静脉树、肌群和随附的建模数据 | Mouse Atlas / Animal Atlas contributors；以 Digimouse 为定位参照，CC BY-SA 4.0。参考文献插图没有作为模型素材分发。 | [总说明](public/models/mouse-teaching/ATTRIBUTION.txt)、[消化等结构](public/models/mouse-teaching/digestive/README.md)、[血管](public/models/mouse-teaching/vascular/README.md)、[肌群](scripts/teaching/muscles/ATTRIBUTION.md) |
| [教学建模脚本](scripts/teaching)及随附的控制点和定位数据 | Mouse Atlas / Animal Atlas contributors；保留原项目对教学几何及生成脚本的 CC BY-SA 4.0 声明。 | [教学建模目录说明](scripts/teaching/README.md) |
| 从 Human Atlas 适配的界面与展开交互，包含样式和展开布局 | Copyright (c) 2026 ashemag；MIT。 | [上游项目](https://github.com/ashemag/human-atlas)、[本仓库保留的上游 MIT 全文](public/licenses/human-atlas.txt) |
| 基于 shadcn/ui 的界面组件 | Copyright (c) 2023 shadcn；MIT。应用依赖的各个 npm 包仍保留各自的版权和许可。 | [shadcn/ui](https://github.com/shadcn-ui/ui)；下附其 MIT 声明。 |

## 模型复用时的署名

Digimouse 对应论文：B. Dogdas, D. Stout, A. F. Chatziioannou, R. M. Leahy (2007). *Digimouse: A 3D Whole Body Mouse Atlas from CT and Cryosection Data*. Physics in Medicine & Biology, 52:577–587. [DOI](https://doi.org/10.1088/0031-9155/52/3/003) · [原始项目](https://neuroimage.usc.edu/neuro/Digimouse)。

如果使用了原始分割和教学补建两类模型，可随文件附上以下说明，并补充你对它们做过的修改：

> 原始标注：Digimouse，Dogdas、Stout、Chatziioannou、Leahy（2007），USC Biomedical Imaging Group / UCLA Crump Institute。表面重建、配色、中文名称与成对区域拆分：Mouse Atlas。教学模型：Mouse Atlas / Animal Atlas contributors，依据原标本位置制作的教学近似。模型许可：[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)。

下载单个结构时，GLB 的 `extras` 附有其具体来源、类别、单位和许可。若转换格式时软件未保留 `extras`，请另附对应的 `ATTRIBUTION.txt`。对 CC BY-SA 素材的再分发和改编应保留适当署名、许可链接、修改说明，并依该许可的相同方式共享条款处理改编作品。请以 [CC BY-SA 4.0 许可全文](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en) 为准。研究作者及所属机构不因此为本图谱或衍生作品背书。

## shadcn/ui · MIT

```text
MIT License

Copyright (c) 2023 shadcn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
