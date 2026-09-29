# U12-10 当前结果分类与主张复核交接

## 当前交付

活动WAIT_DEP、依赖A-05、2人日，未领取未签署。本轮归档四旧候选、修正未注册入口，复用外部审计的result_classifier.py。原工具副本归档，活动工具只改两处帮助文字，解决Python3.14 argparse遇裸百分号无法启动的问题；分类算法不变，源包保持不变。15个固定合成案例可重跑，不是阶段一真实分类、研究关闭或独立复核。

## 输入与职责

A-05消费E-04锁库和揭盲授权、A-01原件、A-02分析集/缺失、A-03/U12-11冻结SAP，给PANAS负性情绪后测经前测与分层调整的beta和95%CI。native=1、abstract=0；native-minus-abstract负值有利原生、正值有利抽象。不能传各组前后变化、未经调整差、PF区间、标准化效应或90%TOST区间冒充主结果。

工具接受人工提供的数值，固定假定这一对比方向和尺度；它不验证锁库、量表许可、分层、模型拟合、阈值是否事前冻结，不计算p值、不执行MI/MNAR，也不证明正式研究批准。实际关注差异须来自U12-11/G-03，不能从合成delta=1复制；当前正式阈值和N仍为空。

情绪无法估计时，由真实分析报告记录原因，不制造0或数值区间。候选接口要求有效数字，affect_assessable=false只表示所给数值不可作效果解读；本轮not_assessable数字是测试用占位，不作为真实缺失编码。

## 分轴分类

方向只按95%CI严格跨越0：上界小于0为NATIVE_LOWER，下界大于0为ABSTRACT_LOWER；触0或跨0均NO_DIRECTION_ESTABLISHED。正方向证据可以成为主发现，不是由原生未显著推导。

delta未冻结时THRESHOLD_NOT_FROZEN；区间严格越过相应±delta才支持对应重要收益，严格位于界内为WITHIN_PRESPECIFIED_PRACTICAL_BOUNDS，触界保留IMPORTANT_EFFECT_NOT_EXCLUDED。统计可辨的小差异与界内标签可同时成立；后者不是确认性等效成功。默认等效关闭，工具始终formal_equivalence_claim_allowed=false；未来如启用，需另外事前冻结方法并实现复核，不修改本工具来事后宣布成功。

functional_guard、delivery_valid和sensitivity独立输入、独立报告。护栏FAIL不隐去有效预设情绪结果；实现效度受限保留方向但限制解释，敏感性改变须披露。工具不从PF/SCCI自动推导效度，SCCI只是操纵检查，不把原生性与隐藏性混为一类。

## 运行与验收

从项目根运行`py -3.14 agent/tasks/U12-10/execution/run_cases.py`重建合成报告；单个已计算区间可调用`py -3.14 agent/tasks/U12-10/execution/result_classifier.py 输入.json`。CLI只输出JSON，不发设备/Unity/TD消息，也不批准正式结果或部署。

软件边界覆盖正反方向、小差异、跨0/触0、±delta触边、空阈值、护栏失效、实现失效、敏感性、非有限数/布尔/字符串/反序区间及90%CI。真实分类必须另交冻结输入、全部预设结果、独立复算、允许主张表和真实第二人签收，不因本轮软件通过迁移WAIT_DEP。

## 上下游

A-05当前空报告仍NOT_RUN，没有真实beta/CI/p/n；[A-05交接](../../A-05/outputs/current-analysis.md)更新为候选工具已具备、正式分类未交付。真实分类交[A-06](../../A-06/outputs/current-scope.md)和[W-02](../../W-02/outputs/current-manuscript.md)，执行[主张规则](claim-rules.md)并保留功能代价及设计边界。U12-07给中立规格不是已写真实主稿；可选阶段三另有估计目标，不能混进本分类。

当前负责人、正式输入、真实结果、独立复核及签收仍缺；不自动发布或给部署推荐。根目录19/19项已迁入human/agent，当前读取和运行入口已验证，业务签收不变。
