const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = 3000;

const BASE = path.join(__dirname, "..");

function readFile(file) {
    try {
        return fs.readFileSync(path.join(BASE, file), "utf8").split("\n").filter(Boolean);
    } catch {
        return [];
    }
}

app.get("/api/stats", (req, res) => {
    res.json({
        approved: readFile("approved.txt"),
        blocked: readFile("blocklist.txt"),
        unchecked: readFile("unchecked.txt")
    });
});

app.use(express.static(__dirname));

app.listen(PORT, () => {
    console.log(`Dashboard running on http://localhost:${PORT}`);
}); 
