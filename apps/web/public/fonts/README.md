# Self-hosted Shifu fonts

These are unmodified WOFF2 distributions of the font families already selected
in `documentation/design.md`. Latin includes pt-BR accented letters; Latin Extended
also supports extended Latin content. Only normal styles are loaded: Instrument
Serif 400, DM Sans variable 100–1000, and JetBrains Mono variable 100–800.

Files were retrieved from the official Google Fonts CSS API and asset service:

https://fonts.googleapis.com/css2?family=DM+Sans:wght@100..1000&family=Instrument+Serif&family=JetBrains+Mono:wght@100..800&display=swap

Each family is licensed under the SIL Open Font License 1.1. The accompanying
`*-OFL.txt` files are copied from https://github.com/google/fonts at commit
`51303ca9e8ac9dcea7b12d307ba568fd0e6fcfca`, from `ofl/dmsans`,
`ofl/instrumentserif`, and `ofl/jetbrainsmono`.

Runtime requests use local `/fonts/` URLs, so rendering does not depend on
access to Google Fonts. `font-display: swap` keeps text visible during loading.

## Asset provenance

- `dm-sans-latin-ext.woff2`: https://fonts.gstatic.com/s/dmsans/v17/rP2Yp2ywxg089UriI5-g4vlH9VoD8Cmcqbu6-K6h9Q.woff2
  SHA-256: `a5d38fe99f930275684999b462c7123faa063d9e44e73b4b241723d884aa0f49`

- `dm-sans-latin.woff2`: https://fonts.gstatic.com/s/dmsans/v17/rP2Yp2ywxg089UriI5-g4vlH9VoD8Cmcqbu0-K4.woff2
  SHA-256: `9fea608a947e67020c33cad9a6fe3d60c54119dfb8cff87768a8117a15ed7543`

- `instrument-serif-latin-ext.woff2`: https://fonts.gstatic.com/s/instrumentserif/v5/jizBRFtNs2ka5fXjeivQ4LroWlx-6zsTjmbI.woff2
  SHA-256: `290e6267dd833bf5f899eba4c29ad0a9b09dbe53f6075b18af38057159e1ff20`

- `instrument-serif-latin.woff2`: https://fonts.gstatic.com/s/instrumentserif/v5/jizBRFtNs2ka5fXjeivQ4LroWlx-6zUTjg.woff2
  SHA-256: `5eb09b5ac0e28b67c2f041c8ba6d244604ca0c0980d65912ab2d47fed84ddc31`

- `jetbrains-mono-latin-ext.woff2`: https://fonts.gstatic.com/s/jetbrainsmono/v24/tDbV2o-flEEny0FZhsfKu5WU4xD1OwG_TA.woff2
  SHA-256: `79bfdab9ba467e26eea4122e6f2567e188dd8a09a8c730d501fc487c4ab99c6e`

- `jetbrains-mono-latin.woff2`: https://fonts.gstatic.com/s/jetbrainsmono/v24/tDbV2o-flEEny0FZhsfKu5WU4xD7OwE.woff2
  SHA-256: `18be452724bfdc236c074ca94a249a7f41a86752c7d04ab258ce9ed5651f6a7e`
