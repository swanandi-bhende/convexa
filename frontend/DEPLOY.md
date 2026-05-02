# Deploying the frontend

This repository uses Next.js (App Router) and Tailwind CSS. Below are recommended steps to deploy to Vercel (fast) or to build artifacts in CI.

## Local build

```bash
cd frontend
npm install
npm run build
npm run start # or `next start`
```

## Vercel (recommended)

- Install Vercel CLI and link the project: `npm i -g vercel` then `vercel login` and `vercel --prod`.
- The default Next config will work; set environment variables in the Vercel dashboard (e.g., RPC keys).

## GitHub Actions (build artifact)

A workflow is provided at `.github/workflows/frontend-build.yml` which installs dependencies and runs `npm run build`.

## Notes for on-chain features

- For on-chain deployments (Hardhat), deploy contracts using the `contracts/` scripts.
- Wallet signing and private keys must never be stored in the repo; use secrets in the deployment platform.

## Presentation / Demo mode

Visit `/presentation` after deploying to showcase the app and toggle Demo Mode to seed sample debates for an offline demo.
