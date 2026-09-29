# ADR-022 Agent可执行底板优先视觉资产流水线

> 状态：ACCEPTED
> 日期：2026-08-19
> 决策：V02-D-014B

## 背景

节点14A已经冻结拆层修正要求，但“先生成整幅画再自动拆层”会暴露三个问题：扁平图没有被遮挡区域的真实像素，自动编辑无法保证公共画布内的逐像素对位，透明边缘和长卷轴接缝也无法仅凭提示词验收。用户授权联网复核并由Agent选择最适合执行的路线。

当前环境核对结果：

- Unity版本为`6000.4.9f1`；
- 项目锁定PSD Importer `13.0.3`；
- Codex可使用图像生成与编辑工具，并可通过本地Pillow和NumPy完成确定性图像处理；
- 当前本机常见路径和`PATH`中未发现Photoshop、Krita、GIMP或ImageMagick；
- 本轮不安装新的图像编辑依赖。

## 联网复核结论

1. OpenAI当前图像工具支持更稳定的指令跟随和参考图编辑，适合作为关键帧与底板候选生成工具，但不构成逐像素一致性保证。
2. Adobe官方提供扩图、内容识别填充和逐层导出能力，适合人工修正长卷轴扩展、遮挡后空洞和透明边缘。
3. Unity PSD Importer可从PSB图层生成Sprite，但官方明确说明导入时会忽略通道、混合模式、图层透明度和图层效果。
4. Unity纹理导入设置还会影响运行时尺寸、压缩和质量，因此源合成正确不等于Unity运行结果正确。

参考：

- <https://openai.com/index/new-chatgpt-images-is-here/>
- <https://helpx.adobe.com/photoshop/desktop/create-open-import-images/create-images/explore-beyond-the-canvas-with-generative-expand.html>
- <https://helpx.adobe.com/photoshop/desktop/repair-retouch/remove-objects-fill-space/remove-objects-with-content-aware-fill.html>
- <https://helpx.adobe.com/photoshop/desktop/save-and-export/export-files-to-different-formats/export-layers-as-files.html>
- <https://docs.unity3d.com/Packages/com.unity.2d.psdimporter@13.0/manual/index.html>
- <https://docs.unity3d.com/6000.4/Documentation/Manual/class-TextureImporter.html>

## 决策

采用以下底板优先路线：

1. 每个天气先生成一张关键帧，仅用于冻结风格、地平线、构图、安全区和颜色关系。
2. 不把扁平关键帧直接自动切割为最终图层。
3. 以关键帧、共同风格锚点和已确认场景规格为参考，从后向前独立制作天空、远景、中景、地面、前景和效果遮罩底板。
4. 每个底板从首次生成起使用相同公共画布和坐标原点；长卷轴按底板独立扩展并保留重叠校验区。
5. Agent使用确定性本地处理完成尺寸、色彩模式、透明通道、文件名、哈希、合成预览、接缝预览和基础像素检查。
6. 自动候选无法通过透明边缘、遮挡后空洞、结构连续性或审美检查时，AI先执行局部编辑或重新生成；连续返工仍失败时才进入人工蒙版、内容补绘和边缘修整。
7. 人工修改后的文件视为新版本，重新生成预览、哈希和Unity截图证据。
8. 运行时权威是已验收的独立PNG底板和组合清单，不直接依赖PSB导入器的合成结果。
9. PSB可作为人工可编辑源文件保留；没有PSB时，全画布无损PNG层、`composition.json`和可重建预览脚本共同构成可编辑源。
10. 场景原生目标、真实实际、累计、降级和双环不进入静态天气底板，由Unity语义层独立实现。

## Agent与人工边界

### Agent负责

- 风格锚点、提示词、负向约束和参考图版本；
- 关键帧及分层底板候选生成和编辑；
- 已有图像分离、遮挡区域补全、长卷轴扩展和失败返工；
- 画布统一、透明通道和文件格式标准化；
- 合成、接缝、遮挡、安全区及运动参考预览；
- 清单、来源记录、文件哈希和版本映射；
- Unity导入、层级装配、视差候选、截图、录像和技术验证。

### 人工门

- 从候选中裁定关键帧和整体美术方向；
- 对Unity连续运动录像中的接缝、提示显著度和整体观看感受进行最终审查；
- 只在AI连续返工仍无法通过时，修正蒙版边缘、遮挡后空洞和透视结构。

人工不承担常规逐层拆分。Krita、GIMP或Photoshop仅为异常修整的可选工具，不构成团队必装基线。AI生成者不能代替独立人工验收人签收同一资产。

## 否决路线

- 否决“单张扁平图直接作为正式长卷轴”；
- 否决“把扁平关键帧一次自动抠图后直接入Unity”；
- 否决“依赖未安装的Photoshop完成全部Agent自动流程”；
- 否决“仅凭PSB导入预览认定运行时合成一致”；
- 否决“为制作方便将语义视觉烘焙进天气底板”。

## 后续门

V-03按工程风险冻结最高风险天气选择与验收输入，U-03完成最小垂直切片，比较独立PNG与PSB候选导入结果并测量内存、接缝和对位。只有该切片通过后才批量生产其余三个天气。
