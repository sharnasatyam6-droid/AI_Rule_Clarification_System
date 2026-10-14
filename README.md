# Rulebook — AI Policy Hub

A Vercel-friendly directory for transparent, searchable course policies on AI use.

## Stack
- Next.js App Router and TypeScript
- Neon Auth (managed Better Auth)
- Neon PostgreSQL
- Vercel

## Status
Initial scaffold is being built. See `.env.example` and the setup instructions here after the first deployment configuration.

## Security model
- Public users can only read published policies.
- Teacher permissions are granted explicitly, never through open public signup.
- All policy mutations are server-side and ownership-checked.
- Secrets belong in local/Vercel environment variables, never in source control.
