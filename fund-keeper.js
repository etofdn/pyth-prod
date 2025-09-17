const { ethers } = require("ethers");

async function fundKeeper() {
    const provider = new ethers.JsonRpcProvider("https://subnets.avax.network/eto/testnet/rpc");
    const fundingWallet = new ethers.Wallet(process.env.PRIVATE_KEY || "0x75de5e9a6ee5b863f3aa44ea9b3b6f17c69c8b74c8c3cdab74e67cc4ad8e26c0", provider);

    const keeperAddress = "0x7c68c42De679ffB0f16216154C996C354cF1161B"; // Keeper wallet address

    console.log("💰 Funding keeper wallet...");

    try {
        // Check current balances
        const fundingBalance = await provider.getBalance(fundingWallet.address);
        const keeperBalance = await provider.getBalance(keeperAddress);

        console.log(`Funding wallet balance: ${ethers.formatEther(fundingBalance)} AVAX`);
        console.log(`Keeper wallet balance: ${ethers.formatEther(keeperBalance)} AVAX`);

        // Send 1 AVAX to keeper
        const tx = await fundingWallet.sendTransaction({
            to: keeperAddress,
            value: ethers.parseEther("1.0"),
            gasLimit: 21000
        });

        console.log(`✅ Funding transaction sent: ${tx.hash}`);

        const receipt = await tx.wait();
        console.log(`🎯 Confirmed in block ${receipt.blockNumber}`);

        const newBalance = await provider.getBalance(keeperAddress);
        console.log(`💳 New keeper balance: ${ethers.formatEther(newBalance)} AVAX`);

    } catch (error) {
        console.error("❌ Funding failed:", error.message);
    }
}

fundKeeper();