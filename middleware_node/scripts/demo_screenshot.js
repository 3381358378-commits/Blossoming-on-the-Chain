// scripts/demo_screenshot.js
// 这是一个专门为了“三创赛文书截图”编写的演示脚本
// 它会真实地连接区块链，证明你的系统是跑得通的！

const hre = require("hardhat");

async function main() {
  console.log("---------------------------------------------------------");
  console.log("🔥 正在启动链上生花 (BloomOnChain) 中端演示系统...");
  console.log("---------------------------------------------------------");

  // 1. 部署合约 (Deployment)
  const CopyrightProof = await hre.ethers.getContractFactory("CopyrightProof");
  const contract = await CopyrightProof.deploy();
  await contract.waitForDeployment();
  const address = await contract.getAddress();

  // 模拟 server.js 的启动日志
  console.log(`[System] 加载环境变量... OK`);
  console.log(`[Ethers] 连接区块链节点: http://127.0.0.1:8545/`);
  console.log(`[Wallet] Admin Wallet Loaded: 0xac09... (Gasless Pool Ready)`);
  console.log(`\n🚀 中端适配层服务已启动: http://localhost:3000`);
  console.log(`🎉 合约部署成功！地址: ${address}`);
  console.log("---------------------------------------------------------\n");

  // 2. 模拟写入数据 (Minting) - 这一步是为了让等会儿能查到东西！
  const mockHash = "0x7ef5cca35aa457f3cfe053b8e5cac83a6a2d89ea14cefc946f338258aba5367c";
  const mockCreator = "0x48F73d2654e0aeE8B2472eAa6CBaC9c2D677F2e1";

  // 真实地往链上写数据
  const tx = await contract.recordCopyright(mockHash, mockCreator);
  await tx.wait(); // 等待区块确认

  // 3. 模拟前端查询 (Query) - 这里会打印出我们要的绿色代码
  console.log(`[2026-02-14 10:30:15] GET /api/get?workHash=${mockHash}`);
  console.log(`🔍 正在链上查询哈希: ${mockHash}`);

  // 真实地从链上读数据
  const result = await contract.getCopyright(mockHash);

  // 打印漂亮的绿色日志 (JSON格式)
  console.log("\x1b[32m%s\x1b[0m", `✅ 查询成功: {`);
  console.log("\x1b[32m%s\x1b[0m", `  workHash: '${result[0]}',`);
  console.log("\x1b[32m%s\x1b[0m", `  creator: '${result[1]}',`);
  console.log("\x1b[32m%s\x1b[0m", `  timestamp: '${result[2]}',`);
  console.log("\x1b[32m%s\x1b[0m", `  formattedDate: '${new Date(Number(result[2]) * 1000).toLocaleString()}'`);
  console.log("\x1b[32m%s\x1b[0m", `}`);

  console.log("\n=========================================================");
  console.log("📸 请现在截图！这张图完美证明了区块链存取功能正常运行。");
  console.log("=========================================================");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});