# Rulebook — AI Policy Hub

Rulebook is a Vercel-friendly web application for students to discover clear, searchable course policies on AI use. The shared administrator workspace lets trusted staff search for a teacher, add a teacher profile, and create, publish, edit, or delete policies under that teacher's name. The original individual teacher sign-in remains available.

## Features

- Public directory of published policies with teacher/title/subject search.
- Filters for subject and AI permission category.
- Policy detail pages with summaries, conditions, and update dates.
- Shared admin sign-in using server-only environment variables and a signed, HTTP-only session cookie.
- Searchable teacher directory and an Add Teacher workflow (searches records already entered; it is not connected to an external college directory).
- Teacher selection before policy editing, with draft/published states.
- Original managed Neon Auth sign-in for individual faculty.
- Server-side authorization for all policy and teacher-management mutations.
- PostgreSQL constraints and indexes, draft/published states, and demonstration seed data.
- Responsive editorial-style UI and baseline security headers.
- GitHub Actions checks for TypeScript, lint, and production build.

## Stack

- Next.js App Router, React, TypeScript
- Neon Auth (Managed Better Auth)
- Neon PostgreSQL
- Vercel

## Local development

1. Install Node.js 22+.
2. Install dependencies: `npm install`
3. Copy `.env.example` to `.env.local`.
4. Fill `DATABASE_URL`, `NEON_AUTH_BASE_URL`, and `NEON_AUTH_COOKIE_SECRET` using the dedicated Rulebook Neon project. Do not commit secrets.
5. For the shared admin workspace, also set `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and a long random `ADMIN_SESSION_SECRET` in `.env.local` and Vercel. Never expose these as `NEXT_PUBLIC_*` variables or commit their values.
6. Start the app: `npm run dev`
7. If using a fresh database, apply `db/schema.sql` to the `neondb` database.

Useful checks:

- `npm run typecheck`
- `npm run lint`
- `npm run build`

## Shared administrator access

Open `/admin`, sign in with the configured `ADMIN_USERNAME` and `ADMIN_PASSWORD`, search existing teacher profiles, or use **Add teacher** to create one. Select a teacher before creating or editing their policies. The add-teacher search only searches profiles already stored in Rulebook; it does not query an external institution directory. Keep the shared login restricted to trusted staff because actions are recorded under the selected teacher's name.

## Teacher access

Teacher access is intentionally provisioned by an administrator. First create the user identity in Neon Auth, then add an approved teacher profile with the exact Auth user ID:

```sql
INSERT INTO teachers (auth_user_id, display_name, email, approved)
VALUES ('AUTH_USER_ID_FROM_NEON_AUTH', 'Teacher Display Name', 'teacher@college.edu', true);
```

Only an approved profile linked to the signed-in identity can manage policies. Never set `approved=true` from a public API request.

## Demonstration content

The initial three policies are **examples only**, not official institutional rules. Replace them with approved course policies before presenting the directory as authoritative.

## Deployment

The project is configured for Vercel and Neon. Set the Neon connection/auth variables and the three server-only admin variables in Vercel. Production email delivery and the correct trusted domain should be configured in Neon Auth before using real faculty accounts. See [Administrator setup](docs/ADMIN_SETUP.md) for details.

## Security notes

- No secrets belong in source control or browser-exposed environment variables.
- Public policy queries return only `published` rows.
- Every teacher mutation checks the session, approved teacher profile, and ownership in SQL.
- Public registration does not grant teacher permissions.
