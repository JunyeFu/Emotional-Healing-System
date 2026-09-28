# 首轮执行输出目录修复

2026-09-29，首轮verify.py完成子进程后写check-1.txt时遇到FileNotFoundError，因为新包evidence目录尚未创建。该次子进程结果未保存，不能引用为通过证据。修正为运行前创建固定evidence目录，随后重跑并保留实际输出。未改业务源码或签署记录。
