# V-04 H3 heat独立素材机器验收记录 v1.0

## 结果

| 字段 | 值 |
|---|---|
| 当前硬门 | `H3_INDEPENDENT_ASSET_KIT` |
| 候选 | `heat-individual-candidate-v1` |
| 素材 | 8个独立PNG |
| 格式 | 全部`RGBA` |
| alpha | 全部包含真实透明像素，四角透明 |
| 清单 | 8/8文件名、职责和SHA-256完整 |
| 评审图 | 由8个独立文件确定性排版生成 |
| 结果 | `READY_FOR_TEAM_DIRECTOR_REVIEW` |

## 素材顺序

1. `cool_air_channel`：目标冷气通道；
2. `cool_air_streaks_near`：实际近场冷气响应；
3. `heat_haze_patch`：局部热扰动；
4. `dust_wisp`：低位矿物扬尘；
5. `salt_crust_cluster`：盐壳前景；
6. `desert_rock_cluster`：浅色荒漠岩石前景；
7. `shallow_channel_glint`：浅沟反光点缀；
8. `cooling_particles`：冷却粒子点缀。

完整素材位于`.artifacts-local/V-04/H3/independent-asset-kit/heat-individual-candidate-v1/`。Git内评审副本位于`review/H3/independent-asset-kit/heat-individual-candidate-v1/`。

## 生成与门控说明

首轮生成图为RGB且带烘焙背景，已被机器门拒绝并仅保留在本地`heat-initial-rgb-v1/`。候选图经过逐项背景提取后重新检查，全部满足RGBA、真实透明像素和透明角点要求。

## 人工门

团队总监需确认：画风匹配、八项独立、目标与实际职责清晰、透明边缘自然、素材可自由组合、无强制构图。还需重点判断`heat_haze_patch`包含的局部盐地纹理是否可接受，以及`cooling_particles`的亮度和冷色是否过强。

本结果不表示storm已获人工确认，也不表示snow、fade、Unity导入、Unity运行、正式构建或资产许可已经完成。
