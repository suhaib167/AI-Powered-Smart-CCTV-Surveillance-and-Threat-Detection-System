/**
 * History page chart — event type distribution from table data.
 */

(function () {
    document.addEventListener("DOMContentLoaded", () => {
        const canvas = document.getElementById("historyChart");
        if (!canvas) return;

        const rows = document.querySelectorAll(".history-table tbody tr");
        const counts = {};

        rows.forEach((row) => {
            const typeCell = row.querySelector(".badge");
            if (!typeCell) return;
            const type = typeCell.textContent.trim().split(":")[0] || "other";
            counts[type] = (counts[type] || 0) + 1;
        });

        const labels = Object.keys(counts);
        const values = Object.values(counts);

        if (labels.length === 0) return;

        new Chart(canvas, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Events",
                    data: values,
                    backgroundColor: "#3b82f6",
                }],
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, ticks: { color: "#8b9cb3", stepSize: 1 }, grid: { color: "#2d3a4f" } },
                    x: { ticks: { color: "#8b9cb3" }, grid: { color: "#2d3a4f" } },
                },
                plugins: { legend: { display: false } },
            },
        });
    });
})();
