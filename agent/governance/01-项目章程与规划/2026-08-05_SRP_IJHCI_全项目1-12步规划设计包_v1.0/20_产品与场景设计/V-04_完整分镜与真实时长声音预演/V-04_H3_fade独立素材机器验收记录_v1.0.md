# V-04 H3 fade独立素材机器验收记录 v1.0

## 结果

| 字段 | 值 |
|---|---|
| 当前硬门 | `H3_INDEPENDENT_ASSET_KIT` |
| 候选 | `fade-individual-candidate-v1` |
| 素材 | 8个独立PNG |
| 格式 | 全部`RGBA` |
| alpha | 全部包含真实透明像素，四角透明 |
| 清单 | 8/8文件名、职责和SHA-256完整 |
| 评审图 | 由8个独立文件确定性排版生成 |
| 结果 | `READY_FOR_TEAM_DIRECTOR_REVIEW` |

## 素材顺序

1. `color_tide_ribbon`：目标色潮带；
2. `actual_reflection_trace`：实际断续反光轨迹；
3. `water_ripple_patch`：局部水波覆盖；
4. `soft_reflection_patch`：柔和环境反射覆盖；
5. `riverbank_grass_cluster`：湿润河岸草簇前景；
6. `wet_pebble_cluster`：湿润卵石前景；
7. `color_bloom_patch`：局部颜色回升点缀；
8. `tributary_glint`：支流反光点缀。

完整素材位于`.artifacts-local/V-04/H3/independent-asset-kit/fade-individual-candidate-v1/`。Git内评审副本位于`review/H3/independent-asset-kit/fade-individual-candidate-v1/`。

## 生成与门控说明

本轮八项首轮输出已直接包含RGBA和真实透明像素，无需二次背景提取。机器门逐项验证透明通道、透明角点、文件命名、职责映射和SHA-256，并从原始独立文件确定性生成评审图。

## 人工门

团队总监需确认：画风匹配、八项独立、目标与实际职责清晰、透明边缘自然、素材可自由组合、无强制构图。还需重点判断目标色潮带与实际断续反光是否明显区分，局部颜色回升是否保持克制且没有替代整屏褪色与复色机制，水波与柔和反射是否具有不同用途。

本结果不表示四天气独立素材已获人工确认，也不表示Unity导入、Unity运行、正式构建或资产许可已经完成。
