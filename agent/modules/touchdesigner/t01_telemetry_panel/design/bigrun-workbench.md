# BigRun Team 工作台

候选：[T01_BigRunWorkbench.toe](../T01_BigRunWorkbench.toe)。旧 [T01_ManualWorkbench.toe](../T01_ManualWorkbench.toe) 和 mock 服务保留，两个工程不能同时监听 UDP5005。

## 使用顺序

1. 自行保存并关闭旧TD/mock，双击新TOE，首页等待数据，不建场、不计时。
2. 设备到手后，按[采集与校准步骤](../../../acquisition/bigrun/README.md)确认地址、ECG/ACC输出率与模式并发。不知道采样率时留空，不填假数值。
3. 仓库根运行：`agent/runtime/start-td-bigrun.cmd --address <已确认地址> --mode observe`。
4. 已核对输出率且有独立参考标定文件时，改用下列命令：

```powershell
agent/runtime/start-td-bigrun.cmd --address <已确认地址> --mode ecg --ecg-hz <实测输出率> --acc-hz <实测输出率> --heart-profile <heart-profile.json完整路径> --resp-profile <resp-profile.json完整路径>
```

5. “准备下一位”进入设备检查页，切换呼吸代理/三轴ACC、ECG/原生RR/心率；“明细”查看标定、时轴和最新消息。“复制采集编号”“打开记录目录”对应候选P-02采集。
6. “确认准备”“开始实验”等实验控制保持禁用：真实SessionCore、Unity、问卷和研究准入尚未接线，不用旧模拟回执放行。检查可取消返回，不生成实验记录。
7. Ctrl+C停止采集。TD显示断流，曲线转历史，实时HR/RR清空；重新运行创建新采集编号、清除旧曲线，不自动续接或开始。

裸双击CMD只显示帮助，不扫描或连接附近设备。`bigrun.cmd capture --td`等价；专用`bigrun_preview`只送本机UDP5005，不使用5007、不向Unity发数据。

## 显示口径

| 对象 | 显示 |
|---|---|
| 设备 | 单台BigRun Team，ECG与ACC来自同一BLE连接 |
| ECG/RR | ECG原始ADC；RR原生整数、单位待核，不冒用μV/ms |
| HR | 原生HR包，或有profile时的ECG过去窗口估计；明细保留来源 |
| 呼吸 | ACC投影代理；未标定/预热/代理待验/断流；相位、屏息、补吸未识别 |
| 运动 | 两组原始XYZ，不提供角速度 |
| 标定 | 文件加载不等于实测通过 |
| 质量/时钟 | 质量未验证；名义采样时轴或主机接收时轴，不是设备同步证明 |
| 实验 | I/G未接入、X未识别、实验桥未接入，无mock身份与历史实验混入 |

保留原12页几何及共同框线，在原生节点替换文案、隐藏角速度和说明性页脚。运行/收尾页保留布局和禁用控制，不伪造真实实验分支。

## 开发与边界

- [采集发布](../../../acquisition/bigrun/td_stream.py)：先写P-02再发布，退出/断连发状态，TD检测各通道及心跳超时。
- [前端模型](../bigrun_preview.py)：拒收旧mock/设备/正式遥测，重复拒收、丢包断线、新采集清空历史。
- [TD运行源码](../../../../tasks/T-01/execution/bigrun_workbench_runtime.py)：不调用实验工作流、不写mock请求。
- [离线打包器](../../../../tasks/T-01/execution/package_bigrun_workbench.py)：不启动TD，源码嵌入TOE；已有文件拒绝覆盖，可用`--out`生成新候选。

已验证范围：合成消息、替身BLE、波形像素、离线TOE展开/脚本编译/共同框线。**TD实开、原生点击/渲染及真实BigRun并发、输出率、时钟、校准误差未验证。**正式联合验收、既有签收与治理状态不变。
