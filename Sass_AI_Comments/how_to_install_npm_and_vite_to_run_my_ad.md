### Quick answer
You don’t need to install Vite globally. It’s already declared in your admin panel’s `devDependencies`. You just need Node.js (which gives you `npm`). Then install dependencies and run the dev server from the `admin_ui` folder.

### Recommended setup (macOS/Linux)
1. Install Node.js via nvm (recommended)
   - Install nvm:
     ```bash
     curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
     # Restart your terminal or:
     export NVM_DIR="$HOME/.nvm"
     [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
     ```
   - Install a compatible Node version (Vite 5 works best with Node 18 or 20):
     ```bash
     nvm install --lts
     nvm use --lts
     node -v
     npm -v
     ```

2. Install project dependencies (from the admin panel folder)
   ```bash
   cd /Users/rahmath.shihabudeen/PycharmProjects/SaasProject/admin_ui
   npm install    # or `npm ci` on CI or if you want an exact, clean install
   ```

3. Run the Vite dev server
   ```bash
   npm run dev
   ```
   - This starts the React admin panel on a local dev server (usually http://localhost:5173). Vite preview uses port 5174 by default as defined in `package.json`.

4. Build and preview production build (optional)
   ```bash
   npm run build
   npm run preview   # serves the production build locally on port 5174 by default
   ```

### Windows (PowerShell)
- Install nvm-windows: https://github.com/coreybutler/nvm-windows/releases
- Then:
  ```powershell
  nvm install lts
  nvm use lts
  node -v
  npm -v
  cd C:\Users\<you>\PycharmProjects\SaasProject\admin_ui
  npm install
  npm run dev
  ```

### Connect admin UI to your API
Your FastAPI backend enables CORS from `CORS_ORIGINS`. Make sure it allows the Vite origin (e.g., `http://localhost:5173`). You can set the env var when running your backend, for example:
```bash
export CORS_ORIGINS="http://localhost:5173,http://localhost:5174"
```
If your React app expects an API base URL, create `.env` in `admin_ui` with something like:
```bash
VITE_API_BASE_URL=http://localhost:8000/v1
```
Then restart `npm run dev`. The script will inject `import.meta.env.VITE_API_BASE_URL` into your code.

### Common issues and fixes
- node/npm not found:
  - Re-open terminal after installing nvm, or source your profile (`source ~/.bashrc` or `source ~/.zshrc`).
  - Ensure `nvm use --lts` is executed in every new shell (or set a default: `nvm alias default lts/*`).

- Port already in use (5173/5174):
  - Stop the other process or run a different port: `npm run dev -- --port 5175`.

- Dependency/build errors:
  - Try a clean install: `rm -rf node_modules package-lock.json && npm install`.
  - Clear cache if needed: `npm cache clean --force` then reinstall.

- CORS errors in browser:
  - Add your Vite origin to `CORS_ORIGINS` env var for the FastAPI app, and restart the backend.

### Summary for your project
- Folder to use: `/Users/rahmath.shihabudeen/PycharmProjects/SaasProject/admin_ui`
- Commands to run:
  ```bash
  # one-time
  nvm install --lts && nvm use --lts

  # per project
  cd /Users/rahmath.shihabudeen/PycharmProjects/SaasProject/admin_ui
  npm install
  npm run dev
  ```

If you’d like, tell me your OS (macOS/Windows/Linux) and I can tailor exact commands, including setting `CORS_ORIGINS` and the appropriate `.env` values for your backend/frontend.