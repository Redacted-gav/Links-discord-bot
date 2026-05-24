async function loadData() {
    const res = await fetch("/api/stats");
    const data = await res.json();

    document.getElementById("approved").innerText = data.approved.length;
    document.getElementById("blocked").innerText = data.blocked.length;
    document.getElementById("unchecked").innerText = data.unchecked.length;

    const list = document.getElementById("approvedList");
    list.innerHTML = "";

    data.approved.slice(-10).forEach(link => {
        const li = document.createElement("li");
        li.textContent = link;
        list.appendChild(li);
    });
}

loadData();
setInterval(loadData, 5000);