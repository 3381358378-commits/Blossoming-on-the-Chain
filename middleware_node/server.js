require('dotenv').config();
const express = require('express');
const { ethers } = require('ethers');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
app.use(cors());
app.use(bodyParser.json());
app.use(express.json()); // 确保解析 JSON 数据

// --- 1. 配置层 ---
const RPC_URL = process.env.RPC_URL;
const PRIVATE_KEY = process.env.ADMIN_PRIVATE_KEY;
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS;

if (!RPC_URL || !PRIVATE_KEY || !CONTRACT_ADDRESS) {
    console.error("❌ 错误：请检查 .env 文件配置");
    process.exit(1);
}

// 连接区块链节点 (Ethers v6)
const provider = new ethers.JsonRpcProvider(RPC_URL);
const adminWallet = new ethers.Wallet(PRIVATE_KEY, provider);

// 合约 ABI (包含确权、查询和事件)
const contractABI = [
    {
        "inputs": [
            { "internalType": "string", "name": "workHash", "type": "string" },
            { "internalType": "string", "name": "creator", "type": "string" }
        ],
        "name": "recordCopyright",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{ "internalType": "string", "name": "workHash", "type": "string" }],
        "name": "getCopyright",
        "outputs": [
            { "internalType": "string", "name": "", "type": "string" },
            { "internalType": "string", "name": "", "type": "string" },
            { "internalType": "uint256", "name": "", "type": "uint256" }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": false,
        "inputs": [
            { "indexed": false, "internalType": "string", "name": "workHash", "type": "string" },
            { "indexed": false, "internalType": "string", "name": "creator", "type": "string" },
            { "indexed": false, "internalType": "uint256", "name": "timestamp", "type": "uint256" }
        ],
        "name": "CopyrightRecorded",
        "type": "event"
    }
];

const contract = new ethers.Contract(CONTRACT_ADDRESS, contractABI, adminWallet);

// --- 接口一：版权确权 (POST) ---
app.post('/api/register', async (req, res) => {
    const { workHash, creator } = req.body;
    if (!workHash || !creator) {
        return res.status(400).json({ success: false, error: "缺少必要参数" });
    }

    try {
        console.log(`🚀 正在发起交易... 作品哈希: ${workHash}`);
        const tx = await contract.recordCopyright(workHash, creator);
        const receipt = await tx.wait(); // 等待区块确认

        console.log(`✅ 存证确认！区块号: ${receipt.blockNumber}`);
        res.json({
            success: true,
            txHash: receipt.hash,
            blockNumber: Number(receipt.blockNumber)
        });
    } catch (error) {
        console.error("❌ 上链失败:", error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// --- 接口二：版权查询 (GET) ---
// 测试指令: curl -X GET "http://localhost:3000/api/get?workHash=xxx"
app.get('/api/get', async (req, res) => {
    const { workHash } = req.query; // 从 URL 参数中读取
    if (!workHash) {
        return res.status(400).json({ success: false, error: "请提供 workHash 参数" });
    }

    try {
        console.log(`🔍 正在链上查询哈希: ${workHash}`);

        // 调用合约 view 函数
        const result = await contract.getCopyright(workHash);

        // 如果返回的哈希为空字符串，说明未找到记录
        if (result[0] === "") {
            return res.status(404).json({ success: false, error: "未找到存证记录" });
        }

        res.json({
            success: true,
            data: {
                workHash: result[0],
                creator: result[1],
                // 注意：Ethers v6 的 BigInt 必须转为字符串才能通过 JSON 发送
                timestamp: result[2].toString(),
                formattedDate: new Date(Number(result[2]) * 1000).toLocaleString()
            }
        });
    } catch (error) {
        console.error("❌ 查询失败:", error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// --- 模块三：实时事件监听 ---
contract.on("CopyrightRecorded", (workHash, creator, timestamp) => {
    console.log(`\n🔔 [实时通知] 检测到新版权确权！`);
    console.log(`   - 作者: ${creator} | 哈希: ${workHash}\n`);
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`\n🌟 中端适配层已就绪！`);
    console.log(`👉 存证接口: POST http://localhost:${PORT}/api/register`);
    console.log(`👉 查询接口: GET  http://localhost:${PORT}/api/get\n`);
});