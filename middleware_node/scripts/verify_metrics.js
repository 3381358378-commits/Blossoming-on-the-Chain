const hre = require("hardhat");

async function main() {
  const [admin, creator] = await hre.ethers.getSigners();
  const started = Date.now();
  const Factory = await hre.ethers.getContractFactory("CopyrightProof");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();
  const deploymentMs = Date.now() - started;

  const workHash = `verify-${Date.now()}`;
  const txStarted = Date.now();
  const tx = await contract.recordCopyright(workHash, creator.address);
  const receipt = await tx.wait();
  const confirmationMs = Date.now() - txStarted;
  const record = await contract.getCopyright(workHash);
  const eventEmitted = receipt.logs.some((log) => {
    try {
      return contract.interface.parseLog(log)?.name === "CopyrightRecorded";
    } catch (_) {
      return false;
    }
  });
  let duplicateRejected = false;
  try {
    await contract.recordCopyright(workHash, creator.address);
  } catch (error) {
    duplicateRejected = String(error).includes("Copyright already exists") || String(error).includes("revert");
  }

  console.log(JSON.stringify({
    metrics: [
      {
        name: "智能合约部署",
        value: { contract_address: await contract.getAddress(), elapsed_ms: deploymentMs },
        unit: "毫秒/地址",
        meaning: "检验 CopyrightProof 合约能否在本地 Hardhat 网络部署并获得地址。",
        interpretation: "部署成功说明合约字节码和本地链环境可用；部署耗时不代表生产链部署耗时。"
      },
      {
        name: "链上确权写入与区块确认",
        value: { tx_hash: receipt.hash, block_number: Number(receipt.blockNumber), gas_used: receipt.gasUsed.toString(), elapsed_ms: confirmationMs },
        unit: "毫秒/Gas/区块",
        meaning: "检验 recordCopyright 是否完成交易提交、区块确认和 Gas 消耗记录。",
        interpretation: "收到回执并包含 Gas，说明本地确权闭环可执行；本地链确认时间不能替代真实网络 10-15 秒的声明。"
      },
      {
        name: "链上查询与数据一致性",
        value: { queried_work_hash: record[0], queried_creator: record[1], timestamp: record[2].toString(), matches: record[0] === workHash && record[1] === creator.address },
        unit: "布尔/时间戳",
        meaning: "检验写入的数据能否通过 getCopyright 原样读取。",
        interpretation: "matches=true 证明写入和读取的数据一致，支持作品指纹可查询验证。"
      },
      {
        name: "版权确权事件发射",
        value: { emitted: eventEmitted },
        unit: "布尔",
        meaning: "检验确权成功后是否发出 CopyrightRecorded 事件，为中端监听和后台审计提供事件依据。",
        interpretation: eventEmitted
          ? "emitted=true 说明链上状态写入同时产生可监听事件；生产环境仍需验证事件监听断线后的补偿和幂等。"
          : "emitted=false 说明当前合约写入成功但没有发出 CopyrightRecorded 事件；Node.js 监听器无法据此生成实时审计通知，应补充 emit 后复测。"
      },
      {
        name: "重复作品哈希拒绝",
        value: { rejected: duplicateRejected },
        unit: "布尔",
        meaning: "检验同一作品哈希能否被合约拒绝重复登记。",
        interpretation: "rejected=true 说明合约具备基础防重复确权约束。"
      }
    ]
  }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});