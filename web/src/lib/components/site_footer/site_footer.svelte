<script lang="ts">
	import { GITHUB_URL } from "$lib/constants";
</script>

<footer class="footer mt-auto">
	<nav class="navbar navbar-expand bg-body-tertiary">
		<div class="container-fluid">
			<div class="collapse navbar-collapse">
				<ul class="navbar-nav me-auto mb-2 mb-lg-0">
					<li class="nav-item">
						<a class="nav-link" href="/volunteer">Volunteer</a>
					</li>
					<li class="mx-1 my-2 vr"></li>
					<li class="nav-item">
						<a class="nav-link" href={GITHUB_URL}><i class="fa-brands fa-github"></i> GitHub</a>
					</li>
				</ul>
			</div>
		</div>
	</nav>
</footer>
