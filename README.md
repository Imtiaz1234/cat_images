# cat_images

A small static collection of images, served as a simple web gallery.

## Development

This repo has no build step or dependencies. It is served as static files.

Start a local server from the repo root:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000/ to view the gallery (`index.html`).

The Cloud Agent environment (`.cursor/environment.json`) starts this server
automatically in a `static-server` terminal on port 8000.
