<script lang="ts">
	import "../app.css";

	import SiteFooter from "$lib/components/site_footer/site_footer.svelte";
	import SiteHeader from "$lib/components/site_header/site_header.svelte";

	let { children } = $props();
</script>

<SiteHeader />
<main class="flex-shrink-0 my-3 container card-body">
	{@render children()}
</main>
<SiteFooter />
