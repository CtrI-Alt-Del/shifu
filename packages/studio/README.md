# @shifu/studio

Local workspace for authoring Shifu motion assets. It currently hosts the
[Text-to-Lottie](https://github.com/diffusionstudio/lottie) player, a Skia
Skottie renderer where coding agents create and preview Lottie animations.
Remotion may join it later.

The player source was copied from `diffusionstudio/lottie` at commit
`3c72912f` under the MIT License (see `LICENSE`), then rewritten from Solid to
React and reorganized to follow the Shifu web layout. Upstream updates cannot be
copied in; port them by hand.

## Source layout

```text
src/
├── constants/          route paths
├── types/              scene and Lottie types
├── utils/              pure Lottie slot logic
└── ui/
    ├── shadcn/         UI primitives
    ├── shared/
    │   ├── hooks/      shared state and scene file I/O: use-scenes, use-ui, use-canvas
    │   ├── styles/
    │   └── widgets/    shared components and the root layout
    └── studio/widgets/ studio layout and pages
```

Shared state uses shared hooks instead of context providers. Each hook keeps
its state in a module-level store (`utils/store.ts`) that React reads with
`useSyncExternalStore`. `use-canvas` owns a single renderer for the page; the
root layout attaches it to the canvas and passes in the current route through
`useCanvasHost`, and every other widget reads it through `useCanvas`. The
playhead updates every animation frame, so only `useCanvasFrame` subscribes
to it.

## Usage

```sh
pnpm install
pnpm --dir packages/studio dev
```

The dev server prefers port `3030` and falls back to the next free port. Use
the URL Vite prints.

Ask your coding agent to create an animation with the `text-to-lottie` skill.
The skill is installed at the repository root and recorded in
`skills-lock.json`; restore it with `pnpm skills`.

## Scenes

Each animation is a scene under `public/projects/<project>/<scene-N>/`:

- `lottie.json` is required;
- `controls.json`, images and fonts are optional and live next to it.

Open a scene at `http://localhost:<port>/<project>/<scene-N>` and pin a frame
with `?frame=<N>`.

## Checks

```sh
pnpm --dir packages/studio check:types
pnpm --dir packages/studio build
```
