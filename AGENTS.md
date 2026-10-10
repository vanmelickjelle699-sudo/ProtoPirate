# AGENTS.md — ProtoPirate (Base44 sandbox)

Non-obvious notes for running this repository in the Base44 sandbox.

## What this project is

This is a **Flipper Zero firmware application** (`.fap`), written in C. It is not
a web app: it has no HTTP server and no browser UI. `application.fam` declares
`apptype=EXTERNAL`, `targets=["f7"]`, and the code lives in `protocols/`,
`scenes/`, `views/`, `helpers/`. It runs on Flipper Zero hardware.

**There is therefore nothing to "see" in a browser.** The Base44 preview on port
3000 shows a generated *build report* page, not the application UI.

## How it is built

`ufbt` (micro Flipper Build Tool) compiles the app into `dist/proto_pirate.fap`.
It self-manages the Flipper SDK and ARM toolchain, downloading them on first run
against the `release` SDK channel (override with `ufbt update --channel=dev|rc`,
or `--index-url=` for Unleashed/Momentum). The upstream CI (`.gitea/workflows/build.yml`)
builds for six SDK variants; the sandbox only needs the default one.

## Running it here

```sh
docker compose -f docker-compose.base44.yml up -d --build
```

- `app` service = `Dockerfile.base44` (Python + ufbt only; source bind-mounted at
  `/project`) running `tools/base44_preview.py`.
- That helper builds the app with `ufbt` on startup and serves a build report on
  **0.0.0.0:3000**: `/` (status page), `/build.log`, and the built `.fap` for
  download. It starts serving immediately and builds in the background, so the
  page loads at once and refreshes itself while compiling.
- The SDK/toolchain cache lives in `/project/.ufbt` and build output in
  `/project/dist` — both already in `.gitignore`, so they never get committed.

## Verifying a change

1. `docker compose -f docker-compose.base44.yml logs app` — look for the build lines.
2. `curl -s http://localhost:3000/ | grep -o 'BUILD [A-Z]*'` — expect `BUILD SUCCESSFUL`.
3. `ls -l dist/proto_pirate.fap` — the compiled artifact.

After editing C sources, rebuild by restarting the service
(`docker compose -f docker-compose.base44.yml restart app`), then `reload_preview`.
There is no dev server / hot reload for firmware.

## Sandbox-specific notes

- `docker-compose.base44.yml` and `Dockerfile.base44` are Base44 sandbox artifacts;
  they do not change how upstream builds the app (that stays `ufbt` via Gitea CI).
- `tools/base44_preview.py` is a sandbox-only helper and is not part of the app.
- No credentials or external services are required to build this project.
