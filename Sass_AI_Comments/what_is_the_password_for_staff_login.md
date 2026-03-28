### Staff login password

It depends on how the staff account was created:

- If the staff user was CREATED via the Users page and no custom password was entered at creation time, the code defaults to `ChangeMe#123` (see `Users/Index.tsx`: when creating a user without an id, it sends `password: newPwd || 'ChangeMe#123'`).
- If a custom password was set during creation or later updated via “Edit User” → “New Password”, then use that custom password.

So, for newly created staff users with no explicit password provided, try:

```
ChangeMe#123
```

You can always reset a staff user’s password from the Users page:
- Open Users → find the user → Edit → set “New Password” → Save.

If you’re logging in to sample/demo data, ensure the staff user exists and is active for the intended tenant. If you need, I can also generate a demo staff user and share the credentials format (email + default password).