### What this script does
- Runs Odoo in shell mode and calls ofh.order.dashboard.refresh_report(FROM_DATE, TO_DATE).
- Commits the transaction and prints a confirmation.

Script path on your machine:
- /Users/rahmath.shihabudeen/ayesha-workspace/repositories/v17/bsi-ayesha-ops/ref.sh

### Prerequisites
- Python 3 available as python3
- Your Odoo environment set up with:
  - odoo-bin at: /Users/rahmath.shihabudeen/ayesha-workspace/repositories/v17/bsi-ayesha-ops/odoo/odoo-bin
  - Config file: /Users/rahmath.shihabudeen/ayesha-workspace/repositories/v17/bsi-ayesha-ops/odoo.cfg
- The target Odoo database exists and is accessible.

### Make the script executable (one-time)
- Open a terminal and run:
  - cd /Users/rahmath.shihabudeen/ayesha-workspace/repositories/v17/bsi-ayesha-ops
  - chmod +x ./ref.sh

### How to run
- Basic run (uses defaults: DB from env or fallback, dates = yesterday..today):
  - ./ref.sh

- Specify only the DB name (dates still default):
  - ./ref.sh my_database

- Specify DB and date range explicitly (YYYY-MM-DD):
  - ./ref.sh my_database 2025-09-01 2025-09-14

- Alternatively set DB via environment variable, then run:
  - DB_NAME=my_database ./ref.sh
  - DB_NAME=my_database ./ref.sh 2025-09-01 2025-09-14

### What dates the script uses
- FROM_DATE default: yesterday (local time)
- TO_DATE default: today (local time)
- Both must be in format YYYY-MM-DD if provided.

### Output you should see
- The script will drop into Odoo shell, execute the refresh, and print something like:
  - Order dashboard refreshed from 2025-09-01 to 2025-09-14 on DB: my_database
  - Refresh completed.

### Common issues and fixes
- Permission denied
  - Ensure the script is executable: chmod +x ./ref.sh
- python3: command not found
  - Install Python 3 or adjust your PATH so python3 is available.
- odoo-bin not found or wrong path
  - Confirm the ODOO_PATH in ref.sh points to the correct odoo directory. Current value:
    - ODOO_PATH="/Users/rahmath.shihabudeen/ayesha-workspace/repositories/v17/bsi-ayesha-ops/odoo"
- Config or DB issues
  - Ensure odoo.cfg exists at the path in the script and that the -d database name exists.
  - If your DB is different from the default, pass it as the first argument or set DB_NAME env var.
- Date format error
  - The script validates YYYY-MM-DD. Example valid: 2025-09-14. Example invalid: 14-09-2025.
- Dependency/database connection errors (e.g., psycopg2, pg connection)
  - Ensure your Odoo environment can connect to PostgreSQL as configured in odoo.cfg.

### Notes for macOS vs Linux
- The script is cross-platform for date handling (works on macOS BSD date and GNU date on Linux).

### Example session
1) Run for default DB and yesterday..today:
- ./ref.sh

2) Run for DB ayesha_prod and an explicit two-week range:
- ./ref.sh ayesha_prod 2025-09-01 2025-09-14

3) Using env var for DB:
- export DB_NAME=ayesha_stage
- ./ref.sh 2025-09-10 2025-09-14

If you’re on Windows, run this from WSL or a Unix-like shell (Git Bash) that has bash and python3.

### Where to change defaults
- Default DB fallback inside the script:
  - DB_NAME_DEFAULT="odoo_db"
- Paths:
  - ODOO_PATH and ODOO_CONFIG at the top of ref.sh. Update them if your checkout paths differ.

Need me to tailor a one-liner for your exact DB and date window? Tell me your DB name and the dates you want.