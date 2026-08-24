---
status: accepted
---

# 使用Python与固定FFmpeg进行确定性预演

V-04不使用Unity或TouchDesigner作为Animatic制作权威，而采用Python 3.14.4、Pillow 12.2.0、NumPy 2.4.6和外部FFmpeg/ffprobe 9.0.1 release essentials构建分层确定性渲染链。工具版本、来源、绝对路径、归档与可执行文件哈希、许可状态进入工具锁；FFmpeg二进制保留在被Git忽略的项目工具目录，只作开发期制作工具。渲染先复用共享环境层，再叠加两套互斥提示层和外部评审层，并按10秒、25秒、200秒、800秒及完整制品逐级放行。该工具选择不表示FFmpeg已安装，也不构成Unity运行或正式构建证据。
