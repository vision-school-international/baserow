# Brand

The product brand lives in one place. To swap it:

1. Set `BRAND_NAME` and `BRAND_URL` in the environment (backend and web-frontend
   read the same variables). Defaults: `Baserow`, `https://baserow.io`.
2. Drop replacement files into `web-frontend/modules/brand/public/img/`, keeping
   core's names: `logo.svg` (app and email logo), `favicon_16.png`, `favicon_32.png`,
   `favicon_48.png`, `favicon_192.png`. A missing file falls back to core's.

Rebuild the image after changing files; env changes only need a restart.
