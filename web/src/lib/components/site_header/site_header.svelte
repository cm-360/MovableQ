<script>
	import { SITE_TITLE } from "$lib/constants";
</script>

<!-- stats.js -->

<nav class="navbar bg-body-tertiary">
	<div class="container-fluid">
		<a class="navbar-brand" href="/">{SITE_TITLE}</a>
		<span class="navbar-text">
			<span id="waitingCount">?</span> jobs in queue,
			<span id="workingCount">?</span> active jobs,
			<span id="workerCount">?</span> workers online,
			<span id="movableTotal">?</span> movables mined
		</span>
	</div>
</nav>
