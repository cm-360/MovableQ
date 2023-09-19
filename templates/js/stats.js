(() => {

  const waitingCount = document.getElementById("waitingCount");
  const workingCount = document.getElementById("workingCount");
  const workerCount = document.getElementById("workerCount");
  const movableTotal = document.getElementById("movableTotal");

  async function getNetworkStats() {
    const response = await fetch("{{ url_for('api_check_network_stats') }}");
    if (response.ok) {
      const responseJson = await response.json();
      const stats = responseJson.data;
      waitingCount.innerText = stats.waiting;
      workingCount.innerText = stats.working;
      workerCount.innerText = stats.workers;
      movableTotal.innerText = stats.mseds_mined;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    getNetworkStats();
    setInterval(getNetworkStats, 15000);
  });

})();
