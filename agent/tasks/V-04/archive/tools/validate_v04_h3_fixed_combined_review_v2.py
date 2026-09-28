from pathlib import Path

import validate_v04_h3_fixed_combined_review as implementation


HERE = Path(__file__).resolve().parent
implementation.CONFIG_PATH = HERE / "V-04_H3固定镜头合并评审配置_v2.0.json"
implementation.MANIFEST_PATH = HERE / "V-04_H3固定镜头合并评审候选清单_v2.0.json"
implementation.REPORT_PATH = HERE / "V-04_H3固定镜头合并评审机器验收记录_v2.0.json"


if __name__ == "__main__":
    implementation.main()
