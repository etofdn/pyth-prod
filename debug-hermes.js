const https = require("https");

const priceIds = [
    "0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe", // META/USD
    "0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688", // AAPL/USD
    "0x297cc1e1ee5fc2f45dff1dd11a46694567904f4dbc596c7cc216d6c688605a1b", // NVDA/USD
    "0xb43660a5f790c69354b0729a5ef9d50d68f1df92107540210b9cccba1f947cc2", // AMZN/USD
    "0x5b1703d7eb9dc8662a61556a2ca2f9861747c3fc803e01ba5a8ce35cb50a13a1"  // GOOGL/USD
];

const priceIdsQuery = priceIds.map(id => `ids[]=${id.replace('0x', '')}`).join('&');
const url = `https://hermes.pyth.network/v2/updates/price/latest?${priceIdsQuery}`;

console.log("URL being called:", url);

const req = https.get(url, (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
        console.log("Response:", data.slice(0, 200));
        try {
            const result = JSON.parse(data);
            console.log("✅ JSON parsed successfully");
            console.log("Number of prices:", result.parsed?.length || 0);
        } catch (error) {
            console.log("❌ JSON parse error:", error.message);
            console.log("Raw response start:", data.slice(0, 100));
        }
    });
});

req.on('error', (error) => {
    console.error("Request error:", error);
});

req.setTimeout(10000, () => {
    req.destroy();
    console.log("Request timeout");
});