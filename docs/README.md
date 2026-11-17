# Quantum Lab Agent website

Static project website published at <https://brun3y.github.io/quantum_lab_agent/>.
The site uses plain HTML, CSS, and JavaScript; no build step or backend is required.
The Python agents run separately on the user's machine. The website presents the
project and recorded demos; it does not connect to IBM Quantum or collect tokens.

## Preview locally

From the repository root:

```sh
python3 -m http.server 4173 --directory docs
```

Open <http://localhost:4173>. Check the desktop and mobile layouts, agent and demo
tabs (including arrow-key navigation), mobile menu, and both copy buttons.

## Deployment

`.github/workflows/pages.yml` publishes `docs/` on pushes to `main` that change the
website or the deployment workflow. It can also be run manually. The repository's
GitHub Pages source must be **GitHub Actions**.

## Assets

- The demos in `images/` are the original project recordings.
- Doto, Manrope, and IBM Plex Mono are self-hosted fonts from Google Fonts, under
  the SIL Open Font License. Their licenses are in `assets/fonts/`.
- The chip, circuit lines, and decorative graphics are native SVG and CSS.
- The design takes inspiration from the PlayerZero page in the supplied Pinterest
  reference: <https://mx.pinterest.com/pin/1141592205571939789/>.
