# 大创项目全栈工程

## 目录

```text
 Blossoming on the Chain/
 ├─ frontend/          静态前端、VR 页面与 flower.glb
 ├─ backend_python/    Flask 业务后端与订单数据
 ├─ middleware_node/   Node.js 区块链中端、合约与 Hardhat 配置
 └─ docs/              项目说明文档
```

## 环境要求

- Python 3.10+
- Node.js 18+
- 已启动并可访问的区块链 RPC
- `middleware_node/.env` 中配置 `RPC_URL`、`ADMIN_PRIVATE_KEY`、`CONTRACT_ADDRESS`

当前 `.env` 使用本地 Hardhat RPC：`http://127.0.0.1:8545/`。因此本地演示需要先启动 Hardhat 节点。

## 启动步骤

### 推荐：一键启动本地演示

在 PowerShell 中执行以下两条命令。脚本会自动启动 Hardhat、本地部署合约、更新 `.env`，并打开 Node、Python 和前端服务窗口：

```powershell
cd 'D:\三创赛\Blossoming on the Chain'
Set-ExecutionPolicy -Scope Process Bypass
.\start-local.ps1
```

脚本启动后访问 `http://localhost:8080/index.html`，管理页面访问 `http://localhost:8080/admin.html`。不要关闭脚本打开的四个服务窗口。

### 手动启动

如果不使用脚本，仍可按下面步骤分别启动服务。每条命令单独执行，不要把下一条 `cd` 粘到上一条命令末尾。

### 0. 启动本地链并部署合约

```powershell
cd 'D:\三创赛\Blossoming on the Chain\middleware_node'
npx hardhat node
```

保持该终端运行，再打开一个终端部署确权合约：

```powershell
cd 'D:\三创赛\Blossoming on the Chain\middleware_node'
npx hardhat run scripts/deploy.js --network localhost
```

部署脚本现在会自动把合约地址写入 `middleware_node/.env`。如果 `.env` 中的管理员私钥不是本次 `hardhat node` 输出的账户私钥，也需要替换为同一个账户的私钥。默认测试账户 #0 的私钥就是当前示例 `.env` 中的私钥。

### 1. 启动 Node.js 区块链中端

```powershell
cd 'D:\三创赛\Blossoming on the Chain\middleware_node'
npm install --legacy-peer-deps --cache "$env:TEMP\dachuang-npm-cache"
npm start
```

中端接口：`http://localhost:3000/api/register`。

### 2. 启动 Python 后端

```powershell
cd 'D:\三创赛\Blossoming on the Chain\backend_python'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install flask flask-cors web3 requests
python BloomBackend.py
```

Python API：`http://localhost:5000`。

### 3. 启动前端静态服务

```powershell
cd 'D:\三创赛\Blossoming on the Chain\frontend'
python -m http.server 8080
```

浏览器访问：`http://localhost:8080/index.html`。不要直接用 `file://` 打开页面，否则浏览器可能限制 GLB、摄像头或 localStorage 行为。

启动成功时，三个终端应分别保持运行，并出现以下端口：

- Node.js 中端：`http://localhost:3000`
- Python 后端：`http://localhost:5000`
- 前端静态服务：`http://localhost:8080`

## 订单与区块链数据流

1. 浏览器访问 `8080` 前端，点击 `Mint NFT & Buy`。
2. 前端请求 Python 的 `POST http://localhost:5000/api/order`。
3. Python 生成作品哈希，并请求 Node.js 的 `POST http://localhost:3000/api/register`。
4. Node.js 使用 `.env` 中的管理员账户和合约地址调用 `recordCopyright`，等待确认后返回真实 `txHash`。
5. Python 将订单写入 `backend_python/orders.json`；管理页面通过 Python 的 `/api/admin/orders` 查看订单。
6. Node.js 终端会实时打印 `CopyrightRecorded` 事件，也可调用 `GET http://localhost:3000/api/get?workHash=作品哈希` 查询链上记录。

## 常用检查

```powershell
Test-NetConnection localhost -Port 3000
Test-NetConnection localhost -Port 5000
Test-NetConnection localhost -Port 8080
```

如果浏览器提示 `ERR_CONNECTION_REFUSED`，说明对应服务没有保持运行；回到对应终端查看错误，不要继续刷新浏览器。

## 说明

- `frontend`、`backend_python`、`middleware_node` 的源代码按原项目归档，除确权请求和 VR 设计参数传递外未做业务重构。
- Python 后端会调用 Node.js 的 `POST /api/register`，只有收到 Node.js 返回的真实 `txHash` 才记录为已确认交易。
- Node.js 服务不可用时，Python 会保存 `pending-...` 状态标识，避免订单接口整体崩溃；该标识不是区块链交易哈希。
- Hardhat 合约部署、测试和脚本仍位于 `middleware_node/contracts`、`middleware_node/ignition`、`middleware_node/scripts` 与 `middleware_node/test`。
当前项目定位：本项目为本地可运行的概念验证与演示原型，不代表生产环境部署方案。IPFS 元数据上传、NFT 标准化发行、真实支付渠道、数据库持久化、身份密钥托管和生产级权限控制仍需进一步完善。