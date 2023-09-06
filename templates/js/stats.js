(() => {

  const waitingCount = document.getElementById("waitingCount");
  const workingCount = document.getElementById("workingCount");
  const minerCount = document.getElementById("minerCount");
  const movableTotal = document.getElementById("movableTotal");

  async function getNetworkStats() {
    const response = await fetch("{{ url_for('api_check_network_stats') }}");
    if (response.ok) {
      const responseJson = await response.json();
      const stats = responseJson.data;
      waitingCount.innerText = stats.waiting;
      workingCount.innerText = stats.working;
      minerCount.innerText = stats.miners;
      movableTotal.innerText = stats.totalMined;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    getNetworkStats();
    setInterval(getNetworkStats, 15000);
  });

})();
