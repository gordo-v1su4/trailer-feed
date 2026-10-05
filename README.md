# Trailer Feed

A video portfolio for importing finished projects, watching versions, comparing takes, and keeping prompts and model metadata alongside the videos.

- Website: https://trailer-feed.vercel.app
- Catalog API: https://media.v1su4.dev/trailer-feed
- Repository: https://github.com/gordo-v1su4/trailer-feed

## Use

Home shows the latest videos. Projects lets you play and compare versions, import another cut, edit its saved prompt and model, and manage the project cover. Import adds a project from finished videos. Prompts and Sources preserve the reference library.

Trailer Feed has no Raycast bridge dependency and does not submit generation jobs. Creative Studio Pro is a separate project. Any future LLM integration will be designed separately.

## Develop

```powershell
bun install
bun run dev
```

Open http://127.0.0.1:5191. The frontend uses the live catalog in development and production. Owner sign-in is required for importing or editing.

```powershell
bun run check
bun run build
bun run test:media
```

See [backend deployment](docs/backend-deployment.md) for the catalog, storage, and runtime configuration, and [rename notes](docs/rename-to-trailer-feed.md) for migration status. Earlier creation and bridge plans under docs/history are historical material.
