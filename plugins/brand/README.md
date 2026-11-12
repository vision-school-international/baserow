# Brand

The product brand lives in one place. To swap it:

1. Set `BRAND_NAME` and `BRAND_URL` in the environment (backend and web-frontend
   read the same variables). The Vision School image sets them in
   `deploy/vsi/Dockerfile`. Without them: `Baserow` and no logo link.
2. Replace the files in `web-frontend/modules/brand/public/img/`: `logo.png` (app and
   email logo), `favicon_16.png`, `favicon_32.png`, `favicon_48.png`,
   `favicon_192.png`.

Rebuild the image after changing files; env changes only need a restart.
