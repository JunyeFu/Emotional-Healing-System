# V-04 H3 snow独立素材机器验收记录 v1.0

## 结果

| 字段 | 值 |
|---|---|
| 当前硬门 | `H3_INDEPENDENT_ASSET_KIT` |
| 候选 | `snow-individual-candidate-v1` |
| 素材 | 8个独立PNG |
| 格式 | 全部`RGBA` |
| alpha | 全部包含真实透明像素，四角透明 |
| 清单 | 8/8文件名、职责和SHA-256完整 |
| 评审图 | 由8个独立文件确定性排版生成 |
| 结果 | `READY_FOR_TEAM_DIRECTOR_REVIEW` |

## 素材顺序

1. `powder_lift_column`：目标粉雪上升柱；
2. `powder_response_near`：实际近场粉雪响应；
3. `snow_mist_patch`：低位雪雾；
4. `drifting_snow_ribbon`：横向飘雪；
5. `snowy_pine_branch`：覆雪松枝前景；
6. `snow_rock_cluster`：覆雪岩石前景；
7. `falling_powder_cluster`：下落粉雪点缀；
8. `settling_powder_cluster`：沉降粉雪点缀。

完整素材位于`.artifacts-local/V-04/H3/independent-asset-kit/snow-individual-candidate-v1/`。Git内评审副本位于`review/H3/independent-asset-kit/snow-individual-candidate-v1/`。

## 生成与门控说明

首轮生成图为RGB且带烘焙背景，已被机器门拒绝并仅保留在本地`snow-initial-rgb-v1/`。候选图经过逐项背景提取后重新检查，全部满足RGBA、真实透明像素和透明角点要求。

## 人工门

团队总监需确认：画风匹配、八项独立、目标与实际职责清晰、透明边缘自然、素材可自由组合、无强制构图。还需重点判断`powder_response_near`的冲击感是否过强，`snow_mist_patch`与`settling_powder_cluster`是否足够区分，以及冷色边缘是否自然。

本结果不表示storm或heat已获人工确认，也不表示fade、Unity导入、Unity运行、正式构建或资产许可已经完成。
