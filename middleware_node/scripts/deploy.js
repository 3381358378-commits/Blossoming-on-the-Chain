const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("正在部署合约...");
  // 获取合约工厂
  const CopyrightProof = await hre.ethers.getContractFactory("CopyrightProof");

  // 部署合约
  const contract = await CopyrightProof.deploy();
  await contract.waitForDeployment();

  // 获取合约地址
  const address = await contract.getAddress();

  const envPath = path.resolve(__dirname, "..", ".env");
  const envText = fs.existsSync(envPath) ? fs.readFileSync(envPath, "utf8") : "";
  const addressLine = `CONTRACT_ADDRESS=${address}`;
  const updatedEnv = /^CONTRACT_ADDRESS=.*$/m.test(envText)
    ? envText.replace(/^CONTRACT_ADDRESS=.*$/m, addressLine)
    : `${envText.trimEnd()}\n${addressLine}\n`;
  fs.writeFileSync(envPath, updatedEnv, "utf8");

  console.log("=============================================");
  console.log("🎉 合约部署成功！");
  console.log("合约地址:", address);
  console.log("✅ 已自动写入 middleware_node/.env");
  console.log("=============================================");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});