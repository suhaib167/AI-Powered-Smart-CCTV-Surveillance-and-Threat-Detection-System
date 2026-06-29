/**
 * Dashboard Chart.js initialization and live stats refresh.
 */

(function () {
    const stats = window.dashboardStats || {};

    function initCharts() {
        const eventsCtx = document.getElementById("eventsChart");
        const sessionCtx = document.getElementById("sessionChart");

        if (eventsCtx) {
            new Chart(eventsCtx, {
                type: "doughnut",
                data: {
                    labels: ["Threats", "Known Faces", "Unknown Faces", "Other Events"],
                    datasets: [{
                        data: [
                            stats.threats || 0,
                            stats.known || 0,
                            stats.unknown || 0,
                            Math.max(0, (stats.total || 0) - (stats.threats || 0) - (stats.known || 0) - (stats.unknown || 0)),
                        ],
                        backgroundColor: ["#ef4444", "#22c55e", "#f59e0b", "#3b82f6"],
                    }],
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: "bottom", labels: { color: "#8b9cb3" } } },
                },
            });
        }

        if (sessionCtx) {
            new Chart(sessionCtx, {
                type: "bar",
                data: {
                    labels: ["Detections", "Alerts"],
                    datasets: [{
                        label: "Current Session",
                        data: [stats.sessionDetections || 0, stats.sessionAlerts || 0],
                        backgroundColor: ["#3b82f6", "#f59e0b"],
                    }],
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true, ticks: { color: "#8b9cb3" }, grid: { color: "#2d3a4f" } },
                        x: { ticks: { color: "#8b9cb3" }, grid: { color: "#2d3a4f" } },
                    },
                    plugins: { legend: { display: false } },
                },
            });
        }
    }

    async function refreshStats() {
        try {
            const response = await fetch("/api/stats");
            if (!response.ok) return;
            const data = await response.json();
            const cards = document.querySelectorAll(".stat-value");
            if (cards.length >= 5) {
                cards[0].textContent = data.total_events ?? 0;
                cards[1].textContent = data.threats_detected ?? 0;
                cards[2].textContent = data.known_faces ?? 0;
                cards[3].textContent = data.unknown_faces ?? 0;
                cards[4].textContent = data.alerts_sent ?? 0;
            }
        } catch (_) {
            /* polling optional */
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        initCharts();
        setInterval(refreshStats, 15000);
    });
})();
