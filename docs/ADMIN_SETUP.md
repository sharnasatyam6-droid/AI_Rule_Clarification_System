# Administrator setup
1. Copy .env.example to .env.local and set DATABASE_URL for the dedicated Rulebook Neon project, NEON_AUTH_BASE_URL for the same branch, and a fresh random NEON_AUTH_COOKIE_SECRET of at least 32 characters.
2. Add these values to Vercel Environment Variables for Production, Preview, and Development. Never commit .env.local or share secrets in issues/chat.
3. Run db/schema.sql against the neondb database. It creates teacher/policy tables, search indexes, and clearly labelled demo policies.
4. Approve a teacher only after creating their identity through Neon Auth. Then insert their exact auth ID: INSERT INTO teachers(auth_user_id,display_name,email,approved) VALUES ('AUTH_USER_ID_FROM_NEON_AUTH','Teacher Display Name','teacher@college.edu',true);
5. Run npm install, npm run typecheck, npm run lint, npm run build. Test that public users see only published policies and teachers cannot change another teacher's policies.
6. Configure production email delivery and trusted domains in Neon Auth. Verify sign-in, sign-out, session restoration, and denial for unapproved users.
