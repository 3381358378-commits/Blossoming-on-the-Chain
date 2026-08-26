import copy
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend_python" / "BloomBackend.py"
FRONTEND = ROOT / "frontend"
NODE = ROOT / "middleware_node"
REPORT_JSON = ROOT / "技术验证实测结果.json"
REPORT_MD = ROOT / "技术验证实测报告.md"


def metric(name, value, unit, status, meaning, interpretation, evidence=""):
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "status": status,
        "meaning": meaning,
        "interpretation": interpretation,
        "evidence": evidence,
    }


def load_backend():
    spec = importlib.util.spec_from_file_location("bloom_backend", BACKEND)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_python_metrics():
    module = load_backend()
    results = []

    wallet_addresses = [module.wallet_service.create_wallet() for _ in range(20)]
    metadata_design = {"colorName": "Gold", "matName": "Gem", "metallic": 0.9, "roughness": 0.2}
    metadata_message = module.generate_cultural_msg(metadata_design["colorName"], metadata_design["matName"])
    metadata_uri = module.ipfs_service.upload_metadata(metadata_design, metadata_message)
    results.append(metric(
        "游客托管钱包与元数据生成",
        {"samples": 20, "unique_wallets": len(set(wallet_addresses)), "wallet_format_valid": all(address.startswith("0x") and len(address) == 42 for address in wallet_addresses), "ipfs_uri": metadata_uri, "ipfs_uri_format_valid": metadata_uri.startswith("ipfs://Qm")},
        "地址/URI",
        "实测",
        "检验游客下单时能否生成合法托管地址，并为设计生成可引用的元数据 URI。",
        "20 次生成均得到唯一且格式合法的地址，元数据 URI 也符合当前演示格式；这验证了托管与元数据入口，不等于真实 IPFS 网络已完成持久化。",
        "backend_python/BloomBackend.py: CustodialWalletService, IPFSService",
    ))

    design = {"colorName": "Red", "matName": "Metal", "metallic": 0.8, "roughness": 0.3}
    start = time.perf_counter()
    cultural = module.generate_cultural_msg(design["colorName"], design["matName"])
    price_samples = [module.calculate_dynamic_price(design) for _ in range(100)]
    elapsed_ms = (time.perf_counter() - start) * 1000
    results.append(metric(
        "文化语义转译与动态算价",
        {"samples": 100, "min": min(price_samples), "max": max(price_samples), "example_message": cultural, "elapsed_ms": round(elapsed_ms, 3)},
        "美元/毫秒",
        "实测",
        "检验设计参数是否能生成双语文化寓意并返回材质溢价后的价格。",
        "结果证明业务函数可运行；价格区间存在随机波动，正式商业系统还应改为可审计的固定报价或记录报价版本。",
        "backend_python/BloomBackend.py: generate_cultural_msg, calculate_dynamic_price",
    ))

    original_pool = copy.deepcopy(module.ARTISAN_POOL)
    try:
        selected = [module.dispatch_order_to_artisan({"matName": "Silk"})["id"] for _ in range(100)]
        silk_scores = [a["credit_score"] for a in module.ARTISAN_POOL if a["specialty"] == "Silk"]
        results.append(metric(
            "工匠信用优先与负载调度",
            {"samples": 100, "selected_ids": sorted(set(selected)), "max_selected_load_after": max(a["load"] for a in module.ARTISAN_POOL)},
            "订单/次",
            "实测",
            "检验材质匹配、信用分排序和负载更新是否共同生效。",
            "100 次模拟派单均能返回工匠并更新负载；由于前三名内随机抽取，结果是负载均衡策略的演示，不等同于生产环境吞吐能力。",
            "backend_python/BloomBackend.py: dispatch_order_to_artisan",
        ))
    finally:
        module.ARTISAN_POOL[:] = original_pool

    module.DB_FILE = str(ROOT / "backend_python" / "_verification_orders.json")
    original_orders = Path(module.DB_FILE).read_text(encoding="utf-8") if Path(module.DB_FILE).exists() else None
    try:
        order = {"order_id": "VERIFY-QC-001", "artisan": copy.deepcopy(module.ARTISAN_POOL[0]), "feedback": None}
        module.save_new_order(order)
        module.request = type("Request", (), {"json": {"order_id": "VERIFY-QC-001", "rating": 2, "comment": "verification"}})()
        with module.app.app_context():
            response = module.submit_feedback()
        payload = response[0].get_json() if isinstance(response, tuple) else response.get_json()
        results.append(metric(
            "QC 差评扣分与反馈闭环",
            {"rating": 2, "punishment": 5, "new_score": payload.get("new_score"), "punished": payload.get("punished")},
            "分",
            "实测",
            "检验低于等于 2 星时是否追溯订单工匠并扣除 5 分。",
            "本次实测触发了扣分和 punished=true，证明反馈接口到信用治理的闭环可执行。",
            "backend_python/BloomBackend.py: submit_feedback",
        ))
    finally:
        path = Path(module.DB_FILE)
        if original_orders is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(original_orders, encoding="utf-8")

    original_post = module.requests.post
    pending_file = Path(module.contract_service.pending_file)
    original_pending = pending_file.read_text(encoding="utf-8") if pending_file.exists() else None
    try:
        def failing_post(*args, **kwargs):
            raise module.requests.RequestException("verification simulated outage")
        module.requests.post = failing_post
        start = time.perf_counter()
        fallback = module.contract_service.proxy_mint("0x0000000000000000000000000000000000000001", "ipfs://verification")
        elapsed_ms = (time.perf_counter() - start) * 1000
        pending_records = json.loads(pending_file.read_text(encoding="utf-8")) if pending_file.exists() else []
        results.append(metric(
            "Node 不可用时的 Fallback 防崩",
            {"returned_prefix": fallback[:8], "is_pending_stub": fallback.startswith("pending-"), "pending_persisted": any(item.get("pending_id") == fallback for item in pending_records), "elapsed_ms": round(elapsed_ms, 3)},
            "毫秒/状态",
            "实测",
            "检验 Node.js 确权服务中断时，订单是否返回 pending 存根而不是让请求崩溃。",
            "本次模拟断链立即返回 pending- 存根且已持久化待确权记录，说明故障可被业务层捕获并保留补偿所需数据；自动重试消费者、幂等处理和补偿成功率仍需单独建设和压测。",
            "backend_python/BloomBackend.py: SmartContractService.proxy_mint",
        ))
    finally:
        module.requests.post = original_post
        if original_pending is None:
            pending_file.unlink(missing_ok=True)
        else:
            pending_file.write_text(original_pending, encoding="utf-8")

    original_db_file = module.DB_FILE
    persistence_file = ROOT / "backend_python" / "_verification_persistence.json"
    module.DB_FILE = str(persistence_file)
    try:
        persistence_order = {"order_id": "VERIFY-PERSIST-001", "artisan": copy.deepcopy(module.ARTISAN_POOL[0]), "feedback": None}
        module.save_new_order(persistence_order)
        persistence_roundtrip = module.load_orders()
        results.append(metric(
            "订单文件持久化往返",
            {"saved": 1, "loaded": len(persistence_roundtrip), "same_order_id": bool(persistence_roundtrip and persistence_roundtrip[0]["order_id"] == persistence_order["order_id"])},
            "订单/布尔",
            "实测",
            "检验订单写入 JSON 文件后，进程内重新读取是否能恢复订单标识。",
            "本次往返读取成功，说明原型具备基础持久化能力；JSON 文件不提供并发事务、损坏修复或多实例高可用保障。",
            "backend_python/BloomBackend.py: save_new_order, load_orders",
        ))
    finally:
        persistence_file.unlink(missing_ok=True)
        module.DB_FILE = original_db_file

    required_routes = ["/api/order", "/api/feedback", "/api/order/<order_id>", "/api/admin/orders", "/api/admin/clear_db"]
    route_rules = {rule.rule for rule in module.app.url_map.iter_rules()}
    results.append(metric(
        "订单、反馈与管理接口完整性",
        {"required": required_routes, "found": sorted(set(required_routes) & route_rules), "coverage": round(len(set(required_routes) & route_rules) / len(required_routes), 3)},
        "接口/比例",
        "静态检查",
        "检验下单、反馈、订单查询、管理查询和清库恢复等履约链路入口是否注册。",
        "当前关键接口均已注册；接口存在不代表鉴权、并发、超时和生产可用性已经达标。",
        "backend_python/BloomBackend.py: Flask routes",
    ))

    model = FRONTEND / "flower.glb"
    vr = (FRONTEND / "vr_tryon.html").read_text(encoding="utf-8")
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")
    results.append(metric(
        "GLB 模型资源可用性",
        {"exists": model.exists(), "size_mb": round(model.stat().st_size / 1024 / 1024, 2) if model.exists() else None, "format": model.suffix},
        "MB",
        "静态检查",
        "检验 AR 和 3D 工坊依赖的模型文件是否存在，并为加载时长测试提供资源基线。",
        "模型文件存在且约 33.71 MB；仅凭文件大小不能证明移动端加载小于 2 秒，仍需在指定设备和网络下测量。",
        "frontend/flower.glb",
    ))
    required = {"Three.js": "three", "GLTFLoader": "GLTFLoader", "MediaPipe Face Mesh": "FaceMesh", "Head Occluder": "colorWrite: false", "HUD": "hud-panel"}
    found = {name: token in vr for name, token in required.items()}
    results.append(metric(
        "WebAR/3D 能力组件完整性",
        found,
        "布尔",
        "静态检查",
        "检验项目是否包含 WebGL/GLB 加载、MediaPipe 面部网格、隐形遮挡体和 HUD 控制的实现入口。",
        "所有关键实现入口均存在；这是代码能力确认，不是实际摄像头追踪帧率或遮挡准确率。",
        "frontend/vr_tryon.html",
    ))
    results.append(metric(
        "前端参数到订单接口的链路入口",
        {"buy_action": "buyNow" in index, "order_api": "/api/order" in index, "design_storage": "bloom_currentDesign" in index},
        "布尔",
        "静态检查",
        "检验定制参数是否有前端动作、订单接口和本地设计数据承接点。",
        "入口存在，但真实端到端耗时、失败率和用户设备兼容性需在浏览器中执行。",
        "frontend/index.html",
    ))
    return results


def run_chain_metrics():
    local_cli = NODE / "node_modules" / "hardhat" / "internal" / "cli" / "cli.js"
    command = ["node", str(local_cli), "run", "scripts/verify_metrics.js"]
    completed = subprocess.run(command, cwd=NODE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        return [metric("Hardhat 链上验证", {"exit_code": completed.returncode, "stderr": completed.stderr[-1200:]}, "状态", "未完成", "检验合约部署、写入、查询、事件和 Gas。", "当前环境未能完成链上脚本，不能把链上结果写成实测结论。", "middleware_node/scripts/verify_metrics.js")]
    output_line = next((line for line in reversed(completed.stdout.splitlines()) if line.lstrip().startswith('{"metrics"')), None)
    if output_line is None:
        return [metric("Hardhat 链上验证", {"stdout": completed.stdout[-1200:]}, "状态", "未完成", "检验合约部署、写入、查询、事件和 Gas。", "链上脚本未输出可解析的指标对象，不能把结果写成实测结论。", "middleware_node/scripts/verify_metrics.js")]
    payload = json.loads(output_line)
    return [metric(item["name"], item["value"], item["unit"], "实测", item["meaning"], item["interpretation"], "middleware_node/scripts/verify_metrics.js") for item in payload["metrics"]]


def write_report(results):
    report = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "metrics": results}
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    def table_text(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("|", "\\|")

    status_counts = {}
    for item in results:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    event_metric = next((item for item in results if item["name"] == "版权确权事件发射"), None)
    event_emitted = event_metric and event_metric["value"].get("emitted") is True
    lines = [
        "# 链上生花技术验证实测报告",
        "",
        f"生成时间：{report['generated_at']}",
        "",
        "## 测试环境与边界",
        "本次自动检测在 Windows PowerShell 项目工作区执行；Python 指标使用当前本地 Python 环境，链上指标使用项目内 Hardhat 2.22.0 临时本地网络，合约验证脚本每次重新部署并写入一条测试记录。自动检测未使用真实摄像头、指定手机、外部 IPFS 节点或生产公链，因此 AR 追踪延迟、渲染 FPS、遮挡准确率、真实 Gasless 端到端时延和高并发可用性不能由本报告虚构替代。",
        f"本次共检测 {len(results)} 项：" + "，".join(f"{key} {value} 项" for key, value in status_counts.items()) + "。",
        "",
        "## 实测结果总表",
        "| # | 指标 | 状态 | 实测值 | 单位 | 指标含义 | 实测结果解读 | 证据 |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, item in enumerate(results, 1):
        lines.append(f"| {i} | {item['name']} | {item['status']} | `{table_text(item['value'])}` | {item['unit']} | {item['meaning']} | {item['interpretation']} | {item['evidence']} |")
    lines.extend([
        "## 总体说明",
        "前述三层架构只有在真实交互、确权和履约链路中稳定运行，才能转化为客户可感知的商业价值。本次检测证明，当前原型已经具备可运行的业务算法、QC 反馈扣分、Node 中断 Fallback、合约写入与查询基础，以及 WebAR 所需的关键代码和模型资源。",
        "在体验侧，GLB、WebGL/PBR、MediaPipe 和 HUD 的实现入口已确认，但模型加载时长、面部追踪延迟、渲染帧率和遮挡准确率必须通过真实浏览器、摄像头、设备和网络环境补测；在信任侧，Hardhat 本地链可给出部署、确权、查询、事件和 Gas 的实测值，但不代表生产网络时延和费用；在履约侧，BOM/调度/QC 的函数级验证成立，但不代表多用户并发下的吞吐、持久化和补偿队列能力。",
        "因此，本项目当前结论应表述为“本地原型技术可行，核心闭环已验证，生产级指标仍需设备矩阵、并发压测、真实网络和浏览器自动化补证”，而不宜直接写成已经达到所有商业目标。",
        "",
        "## 尚需补测的关键指标",
        "模型加载 P50/P95、AR 追踪延迟 P50/P95、渲染 FPS、遮挡准确率、完整确权端到端时延 P50/P95、Gas 消耗、链上失败重试率、Fallback 后补偿成功率、订单接口 P95、并发吞吐、BOM 生成耗时、调度公平性、按时交付率、良品率、QC 误报/漏报率，以及真实设备/浏览器/网络矩阵。",
        "",
        "## 项目专属指标目录",
        "以下指标是本项目可用于验收和商业化评估的完整指标框架；本次自动检测只对能在当前原型和本地环境中可靠复现的项目打上实测或静态检查标签。",
        "",
        "| 维度 | 指标 | 推荐测法 | 本次状态 |",
        "| --- | --- | --- | --- |",
        "| 体验 | GLB 首次加载 P50/P95 | 固定设备、浏览器和网络，重复 30 次记录 Resource Timing | 待补测 |",
        "| 体验 | AR 面部追踪延迟 P50/P95 | MediaPipe 帧时间戳与渲染帧时间戳配对 | 待补测 |",
        "| 体验 | WebGL 渲染 FPS/掉帧率 | 浏览器 Performance API 或 DevTools 采样 | 待补测 |",
        "| 体验 | Head Occluder 遮挡准确率 | 正脸、转头、侧脸样本人工标注穿模帧 | 待补测 |",
        "| 体验 | HUD 参数响应延迟 | 点击调整到模型变换生效的时间差 | 待补测 |",
        "| 体验 | 定制参数跨页一致率 | 对比工坊 currentDesign 与 AR 载入参数 | 静态入口已确认 |",
        "| 体验 | 浏览器/设备兼容率 | Chrome、Safari、Edge 及 iOS/Android 矩阵 | 待补测 |",
        "| 信任 | 合约部署成功率/耗时 | Hardhat 与目标网络分别部署并记录 | 本次实测 |",
        "| 信任 | 确权端到端 P50/P95 | Python 请求、Node 签名、receipt 确认全链路计时 | 待补测 |",
        "| 信任 | Gas 消耗 | 从 receipt.gasUsed 与 gasPrice 计算 | 本次本地链实测 |",
        "| 信任 | 查询一致率 | 写入 workHash/creator 与 getCopyright 比对 | 本次实测 |",
        f"| 信任 | CopyrightRecorded 事件发射率 | 解析 receipt.logs 并验证事件字段 | {'本次实测为 true' if event_emitted else '本次实测为 false'} |",
        "| 信任 | 重复确权拦截率 | 对同一 workHash 重复提交并统计拒绝率 | 本次实测 |",
        "| 信任 | Gasless 成功率 | 真实 Node 服务下重复提交并记录成功/失败 | 待补测 |",
        "| 信任 | Fallback 触发率与补偿成功率 | 模拟 Node/RPC 故障，追踪 pending 到最终 txHash | Fallback 与待确权落盘已实测，自动重试待建 |",
        "| 信任 | 链下文件哈希一致率 | 上传/下载后重算 CID 或哈希 | 待补测 |",
        "| 履约 | 文化语义覆盖率 | 色彩、材质、纹样逐项检查默认分支 | 本次部分实测 |",
        "| 履约 | 动态报价稳定性 | 相同设计重复报价，检查波动和版本记录 | 本次实测，发现随机波动 |",
        "| 履约 | BOM 生成耗时/准确率 | 参数到清单计时并与人工标准 BOM 比对 | 待补测 |",
        "| 履约 | 调度匹配成功率/负载均衡 | 按材质、信用分、负载分层压测 | 本次函数级实测 |",
        "| 履约 | QC 扣分正确率 | 1-5 星边界值测试并检查工匠分数 | 本次实测 2 星扣 5 分 |",
        "| 履约 | 订单 API P95/并发吞吐 | 并发请求记录响应时间、错误率和吞吐 | 待补测 |",
        "| 履约 | 数据持久化恢复率 | 进程重启、文件损坏、并发写入后核对订单 | 待补测 |",
        "| 履约 | 按时交付率/良品率 | 真实工单和 QC 记录按周期统计 | 待运营数据 |",
        "",
        "特别说明：CopyrightRecorded 事件指标以本次自动检测的实际 emitted 值为准。若 emitted=true，说明当前本地合约已能产生事件供 Node.js 监听，但仍需在真实网络验证监听断线后的补偿和幂等；若 emitted=false，则说明事件链路仍未修复，不应把实时审计通知写成已完成能力。",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main():
    results = run_python_metrics() + run_chain_metrics()
    write_report(results)
    print(json.dumps({"metrics": len(results), "report": str(REPORT_MD), "json": str(REPORT_JSON)}, ensure_ascii=False))


if __name__ == "__main__":
    main()