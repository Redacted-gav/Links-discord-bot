const { fetchURL } = require("./fetch.js");

async function iboss(url) {
  const res = await fetchURL(
    "https://cluster122287-swg.ibosscloud.com:8026/json/mobileClient/performUrlFiltering?securityKey=29XA3PD231&userEmail=yo&overrideRequest=false&url=" +
    encodeURIComponent(url)
  );

  const json = await res.json();

  return [
    json.blockReason || "iBoss",
    Boolean(json.blockUrl)
  ];
}

module.exports = { iboss };
