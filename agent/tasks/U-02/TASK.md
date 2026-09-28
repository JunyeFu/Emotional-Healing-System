# U-02【Unity】四层SceneAdapter实现与降级

## 责任与状态

- 注册表DONE；原执行Codex(Grip)/小彬，分支codex/u-02-grip，约3人日。
- 原候选9078bc19f1efa2a512e2bb4992568c869fa895b2，原证据ab25a6b8df85c1326164eb8f9f0804d6d790dc87。
- 傅钧烨2026-09-21真实第二人签收，提交33c33333c95b4465cdb279a0329010856ff0acb0。本轮Codex整理及修复，不把原签名转移到新代码。

## 完成标准

AC1四层单独变化不串扰，符合V-03映射；AC2锁定后累计不变，重置只发生在合法模块/会话边界；AC3降级不伪造成功，背景不泄露节律。

本轮归档可读取的历史四项证据，固定当前执行结构，先修复实际契约偏离，再生成总结Word及项目串联审阅。

## 过程与命令

1. inputs/sources.json定位签署、参数、ADR与实现；archive/evidence-v1保留证据分支127文件原字节。
2. execution/verify.ps1或py -3.14 execution/verify.py实际执行105项EditMode（U-02专项88、U-01共14、F-03共3）与3项PlayMode，并验证历史证据。
3. execution/generate_demo.ps1构建受控开发演示，隐藏运行并录制实际离屏渲染五阶段120帧；逐帧像素检查、ffmpeg/ffprobe编码与解码验证，开发EXE只存.artifacts-local。
4. 读取本轮结果和独立Agent复核，先修正outputs/current-adapter-contract.md及summary.json，再用共享工具生成Word并逐页审阅。
5. 明确路径提交推送，后续补丁真实签收单独进行。任务DONE与本轮规范化进度分开记录。

## 固定归属

inputs存来源，execution存主机命令，evidence存本轮结果，outputs存当前说明与总结，archive存原证据和已被修复的失败尝试。Unity程序集、DevTools、Tests在共享工程中保留有效归属，最终随工程迁入Agent模块层。

## 上下游与技能

上游F-03/F-05/V-03；输入源IV03TelemetrySource。U-01负责网络身份及旧帧门，P-01负责流程；本包不生成研究顺序。V-05/U-03扩展实际天气呈现和渲染回执，I-01验证真实链。

C#、Unity程序集与生命周期、分层投影、Edit/Play测试。国内教学链接由项目08_任务技能与国内学习资料_v1.0.md的L-UNITY/L-UNITYTEST提供；[Unity中文学习平台](https://learn.u3d.cn/)作为实践入口。
