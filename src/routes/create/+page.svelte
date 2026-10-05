<script lang="ts">
  import UploadProject from '$lib/components/UploadProject.svelte';
</script>

<svelte:head><title>Import · Trailer Feed</title></svelte:head>

<div class="studio-column">
  <header><h1 class="t-page">Import a project</h1></header>
  <p class="intro">Add finished videos to your portfolio. Review each version and keep its prompt and model alongside it.</p>
  <UploadProject />
</div>

<style>
  header { margin-bottom: 16px; }
  .intro { margin: 0 0 24px; color: var(--dc-text-muted); font-size: 14px; line-height: 1.6; }
</style>
