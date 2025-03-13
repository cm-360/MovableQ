<script lang="ts">
	import { DISCORD_NAME, DISCORD_URL, ID0_HELP_URL, SITE_TITLE } from "$lib/constants";

	import Step_1 from "$lib/components/cards/step_1/step_1.svelte";
	import Step_2 from "$lib/components/cards/step_2/step_2.svelte";
	import Step_3 from "$lib/components/cards/step_3/step_3.svelte";
	import Step_4 from "$lib/components/cards/step_4/step_4.svelte";
	import Step_5 from "$lib/components/cards/step_5/step_5.svelte";
</script>

<!-- client.js -->

<div class="alert alert-info" role="alert">
	If you have any issues, try refreshing the page. You can also ask for help on the <a
		class="link-info"
		href={DISCORD_URL}>{DISCORD_NAME} Discord</a
	>.
</div>
<div class="d-grid gap-3">
	<div class="card">
		<h4 class="card-header">Welcome to {SITE_TITLE}!</h4>
		<div class="card-body">
			<p class="card-text">
				Welcome to <strong>{SITE_TITLE}</strong>, a service made possible by volunteers with
				powerful GPUs! This site helps to obtain your console's unique encryption key (<code
					>movable.sed</code
				>) by bruteforcing it with a powerful GPU. To get started, choose a method below.
			</p>
		</div>
	</div>
	<div>
		<Step_1 />
		<Step_2 />
		<Step_3 />
		<Step_4 />
		<Step_5 />
	</div>
</div>
<div class="modal fade" tabindex="-1" id="canceledModal">
	<div class="modal-dialog">
		<div class="modal-content">
			<div class="modal-header">
				<h5 class="modal-title">Mining Canceled</h5>
				<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
			</div>
			<div class="modal-body">
				<p>The mining job was canceled, either in another tab or by an administrator.</p>
			</div>
			<div class="modal-footer">
				<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Dismiss</button>
			</div>
		</div>
	</div>
</div>
<div class="modal fade" tabindex="-1" id="failedModal">
	<div class="modal-dialog">
		<div class="modal-content">
			<div class="modal-header">
				<h5 class="modal-title">Mining Failed</h5>
				<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
			</div>
			<div class="modal-body">
				<p>
					We were not able to successfully complete your mining request. To resolve the issue,
					please first verify that you entered all information correctly:
				</p>
				<ul>
					<li>
						Ensure you entered the correct ID0 by copy-pasting the 32-character folder name inside
						your &quot;Nintendo 3DS&quot; folder. If you have multiple, follow the steps <a
							href={ID0_HELP_URL}>here</a
						> to determine the correct one.
					</li>
					<li>
						Ensure that your Mii QR code belongs to the console you are attempting to mine for.
					</li>
					<li>
						Ensure you selected the correct model for your console. As a reference, new consoles
						have 4 shoulder buttons (L,ZL,ZR,R), while old consoles only have 2 (L,R).
					</li>
				</ul>
				<p>
					If you are sure all information is correct and the job still cannot be completed, please
					reach out on the <a class="link" href={DISCORD_URL}>{DISCORD_NAME} Discord</a>.
				</p>
			</div>
			<div class="modal-footer">
				<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Dismiss</button>
			</div>
		</div>
	</div>
</div>
