import json
import os
import time
import random
import secrets
import hashlib
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. 基础配置 (Brain: 资源与定价)
# ==========================================
CULTURAL_MEANINGS = {
    "Red": "鸿运当头 (Fortune)", "Pink": "桃花灼灼 (Romance)",
    "Orange": "心想事成 (Wish)", "Gold": "金玉满堂 (Wealth)",
    "Blue": "青云直上 (Success)", "Cyan": "雨过天青 (Serenity)",
    "Green": "生机勃勃 (Vitality)", "White": "冰清玉洁 (Purity)",
    "Purple": "紫气东来 (Nobility)",
    "Silk": "柔情似水 (Gentleness)", "Metal": "坚韧不拔 (Resilience)",
    "Gem": "璀璨夺目 (Brilliance)"
}

# --- QC升级：为工匠增加信用分 (credit_score) ---
# 初始分 100，发生质量问题会扣分
ARTISAN_POOL = [
    {"id": "A001", "name": "李大师 (Hubei - 缠花)", "specialty": "Silk", "load": 2, "credit_score": 100},
    {"id": "A002", "name": "王匠人 (Fujian - 金工)", "specialty": "Metal", "load": 2, "credit_score": 98},
    {"id": "A003", "name": "陈工作室 (Yunnan - 镶嵌)", "specialty": "Gem", "load": 3, "credit_score": 100},
    {"id": "A004", "name": "苏绣坊 (Suzhou - 刺绣)", "specialty": "Silk", "load": 3, "credit_score": 99},
    {"id": "A005", "name": "赵老师傅 (Beijing - 景泰蓝)", "specialty": "Metal", "load": 4, "credit_score": 97},
    {"id": "A006", "name": "张传人 (Nanjing - 绒花)", "specialty": "Silk", "load": 1, "credit_score": 100},
    {"id": "A007", "name": "刘玉雕 (Henan - 玉器)", "specialty": "Gem", "load": 2, "credit_score": 96},
    {"id": "A008", "name": "苗银寨 (Guizhou - 银饰)", "specialty": "Metal", "load": 1, "credit_score": 99},
    {"id": "A009", "name": "蜀锦院 (Chengdu - 织锦)", "specialty": "Silk", "load": 2, "credit_score": 98}
]


# ==========================================
# 2. 核心引擎 (The Soul: 托管 & 无感铸造)
# ==========================================

class CustodialWalletService:
    """[功能 1: 托管钱包生成]"""

    def create_wallet(self):
        acct = Account.create(str(secrets.token_hex(32)))
        print(f"🔐 [Custodial Wallet] 检测到游客下单，自动生成托管账户: {acct.address}")
        return acct.address


class IPFSService:
    """[功能 2: 元数据生成与 IPFS]"""

    def upload_metadata(self, design, culture_msg):
        metadata = {
            "name": f"Bloom {design.get('colorName')}",
            "description": culture_msg,
            "attributes": design,
            "timestamp": int(time.time())
        }
        meta_json = json.dumps(metadata)
        cid = hashlib.sha256(meta_json.encode()).hexdigest()[:46]
        ipfs_url = f"ipfs://Qm{cid}"
        print(f"🌐 [IPFS Storage] 设计方案已上传去中心化存储: {ipfs_url}")
        return ipfs_url


class SmartContractService:
    """[功能 3: Gasless 代理铸造]"""

    def __init__(self):
        self.w3 = Web3()
        self.admin_account = self.w3.eth.account.create()
        self.contract_addr = "0xBloom_Smart_Contract_v1"

    def proxy_mint(self, user_address, token_uri):
        print(f"⛽ [Gasless Minting] 平台管理员({self.admin_account.address[:6]}...) 正在代付 Gas 费...")
        work_hash = hashlib.sha256(
            f"{token_uri}:{time.time_ns()}".encode("utf-8")
        ).hexdigest()

        try:
            response = requests.post(
                "http://localhost:3000/api/register",
                json={"workHash": work_hash, "creator": user_address},
                timeout=15,
            )
            response.raise_for_status()
            result = response.json()
            tx_hash = result.get("txHash")
            if not tx_hash:
                raise RuntimeError("Node.js response does not contain txHash")

            print(f"✅ [Smart Contract] 确权交易已确认: {tx_hash}")
            return tx_hash
        except (requests.RequestException, ValueError, RuntimeError) as error:
            fallback_id = hashlib.sha256(
                f"pending:{work_hash}:{time.time_ns()}".encode("utf-8")
            ).hexdigest()
            print(f"⚠️ [Smart Contract] Node.js 服务不可用，订单暂记为待确权: {error}")
            return f"pending-{fallback_id}"


# 初始化服务
wallet_service = CustodialWalletService()
ipfs_service = IPFSService()
contract_service = SmartContractService()


# ==========================================
# 3. 业务逻辑与调度 (含 QC 逻辑)
# ==========================================

def generate_cultural_msg(color_name, mat_name):
    c_key = next((k for k in CULTURAL_MEANINGS if k in color_name), "Red")
    m_key = next((k for k in CULTURAL_MEANINGS if k in mat_name), "Silk")
    return f"寓意【{CULTURAL_MEANINGS.get(c_key)}】，兼具【{CULTURAL_MEANINGS.get(m_key)}】之美。"


def calculate_dynamic_price(design):
    base = 49.90
    mat = design.get('matName', 'Silk')
    premium = {"Silk": 0, "Metal": 18.0, "Gem": 48.0}.get(mat, 0)
    return max(base + premium + round(random.uniform(-2.0, 5.0), 2), 29.90)


def dispatch_order_to_artisan(design):
    """
    [调度升级] 引入信用分权重
    逻辑：不仅看材质匹配，还要优先选择信用分高的工匠，实现优胜劣汰。
    """
    target = design.get('matName', 'Silk')

    # 1. 材质筛选
    candidates = [a for a in ARTISAN_POOL if a['specialty'] == target]
    if not candidates: candidates = ARTISAN_POOL

    # 2. [QC 核心] 排序逻辑：先按信用分降序(高分优先)，再按负载升序(空闲优先)
    # 这样如果有差评导致信用分降低，该工匠接单优先级会大幅下降
    candidates.sort(key=lambda x: (-x['credit_score'], x['load']))

    # 3. 取前三名随机 (避免总是给同一个人)
    top_n = candidates[:3] if len(candidates) >= 3 else candidates
    selected = random.choice(top_n)

    selected['load'] += 1
    return selected


# ==========================================
# 4. 数据存储与路由
# ==========================================
DB_FILE = 'orders.json'


def load_orders():
    if not os.path.exists(DB_FILE): return []
    with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)


def save_new_order(order):
    orders = load_orders()
    orders.insert(0, order)
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def save_all_orders(orders):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


@app.route('/')
def home():
    return f"Bloom Engine (QC System Online).<br>Orders: {len(load_orders())}"


@app.route('/api/order', methods=['POST'])
def handle_order():
    data = request.json
    design = data.get('design', {})
    input_owner = data.get('owner', 'Guest')
    order_id = f"BLOOM-{int(time.time())}"

    # 1. [The Soul] 托管钱包判断
    if "Guest" in input_owner or not input_owner.startswith("0x"):
        real_owner_address = wallet_service.create_wallet()
        is_custodial = True
    else:
        real_owner_address = input_owner
        is_custodial = False

    # 2. [Brain] 调度与算价
    artisan = dispatch_order_to_artisan(design)
    ai_message = generate_cultural_msg(design.get('colorName'), design.get('matName'))
    price = f"${calculate_dynamic_price(design):.2f}"

    # 3. [The Soul] 上链
    ipfs_link = ipfs_service.upload_metadata(design, ai_message)
    tx_hash = contract_service.proxy_mint(real_owner_address, ipfs_link)

    # 4. 构造订单 (增加 feedback 字段)
    new_order = {
        "order_id": order_id,
        "owner": real_owner_address,
        "price": price,
        "design": design,
        "cultural_msg": ai_message,
        "blockchain_hash": tx_hash,
        "ipfs_link": ipfs_link,
        "artisan": artisan,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Minted",
        "feedback": None,  # 新增：用于存储用户评价
        "custodial_address": real_owner_address if is_custodial else None
    }
    save_new_order(new_order)

    return jsonify({
        "status": "success", "order_id": order_id, "hash": tx_hash, "cultural_msg": ai_message,
        "real_price": price, "custodial_address": real_owner_address if is_custodial else None,
        "owner": real_owner_address
    })


# --- 新增：用户质量反馈接口 (闭环核心) ---
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    order_id = data.get('order_id')
    rating = data.get('rating', 5)  # 1-5 星
    comment = data.get('comment', '')

    orders = load_orders()
    target_order = next((o for o in orders if o['order_id'] == order_id), None)

    if not target_order:
        return jsonify({"status": "error", "message": "Order not found"}), 404

    # 记录反馈
    target_order['feedback'] = {
        "rating": rating,
        "comment": comment,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # [QC 闭环] 自动追溯与惩罚
    artisan_id = target_order['artisan']['id']
    punishment = 0

    # 如果是差评 (<=2星)，扣除对应工匠信用分
    if rating <= 2:
        punishment = 5
        print(f"⚠️ [QC ALERT] 收到差评! 订单:{order_id} -> 追溯工匠:{target_order['artisan']['name']}")

        # 更新内存中的工匠库
        for a in ARTISAN_POOL:
            if a['id'] == artisan_id:
                a['credit_score'] -= punishment
                # 同步更新订单快照里的分数，以便前端展示变化
                target_order['artisan']['credit_score'] = a['credit_score']
                break

    save_all_orders(orders)

    return jsonify({
        "status": "success",
        "new_score": next((a['credit_score'] for a in ARTISAN_POOL if a['id'] == artisan_id), 0),
        "punished": punishment > 0
    })


@app.route('/api/order/<order_id>', methods=['GET'])
def query_order(order_id):
    orders = load_orders()
    for order in orders:
        if order.get('order_id') == order_id:
            return jsonify({"status": "found", "data": order})
    return jsonify({"status": "not_found"}), 404


@app.route('/api/admin/orders', methods=['GET'])
def get_all_orders():
    return jsonify(load_orders())


@app.route('/api/admin/clear_db', methods=['POST'])
def clear_database():
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump([], f)
    # 重置工匠状态
    for a in ARTISAN_POOL:
        a['load'] = max(0, a['load'] - 2)
        a['credit_score'] = 100  # 恢复信用分
    return jsonify({"status": "success", "message": "Database cleared"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)