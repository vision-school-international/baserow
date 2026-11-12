# Brand

The product brand lives in one place. To swap it:

1. Set `BRAND_NAME` in the environment (backend and web-frontend read the same
   variable). The Vision School image sets it in `deploy/vsi/Dockerfile`. Without it:
   `Baserow`. The logo never links anywhere.
2. Replace the files in `web-frontend/modules/brand/public/img/`: `logo.png` (app and
   email logo), `favicon_16.png`, `favicon_32.png`, `favicon_48.png`,
   `favicon_192.png`.

Rebuild the image after changing files; env changes only need a restart.
