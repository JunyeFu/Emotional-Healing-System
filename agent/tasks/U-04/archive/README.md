# U-04 旧Unity生产工具归档

PROJECT_FRAMEWORK.md为旧Unity工程说明，包含TD/Spout、旅人卷动和StormScene已完成等旧范围陈述。原文迁入本目录，工程原位置只保留当前入口说明；旧“已完成”不用于U-04验收。

SetupWeatherScenes.cs与SetupWeatherWalkScene.cs及各自meta原文归档。它们从Editor菜单批量保存旧场景或创建旅人、盾牌、行走和闪电；与固定镜头无屏幕内旅人方向冲突，不是当前生产工具。

迁移前已检查工程C#及Unity场景、Prefab、asset中的类名和GUID，无外部引用，保留原GUID但移出Assets停止自动编译与菜单注册。实际StormScene与WeatherDirector仍有旧序列化引用，暂不删除；共享模块完整清理另在整体迁移中处理。

此归档保留共享原型迁移依据，不表示U-04已获storm分配，也不表示归档材料由U-04独占。没有本包历史签署或运行验收。
