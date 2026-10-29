# Contributing

Contributions that improve Egyptian source access, pagination, full text,
failure visibility, portability, Arabic text handling or documentation are welcome.

1. Fork this repository and create a focused branch.
2. Install the paired Python library and run `npm ci --ignore-scripts`.
3. Add a synthetic regression fixture for any concrete parser or boundary bug.
4. Run `EGYPT_JOBS_PYTHON=/path/to/python npm test` and `node smoke.mjs`.
5. Open a pull request explaining the behavior, evidence and remaining limits.

Keep these contracts: read-only tools, source URL boundaries, full text distinct
from cards, truthful pagination, raw uncertain dates, explicit access failures
and no claim of model review or whole-market coverage. Honor source attribution,
rate limits and content conditions in [SOURCE_POLICY.md](SOURCE_POLICY.md).

Do not contribute source datasets, screenshots, real employer descriptions,
account/profile records, authentication material, stealth transports or access
bypass code. Record copied upstream code precisely and preserve its copyright
and complete compatible license notice. Reference credits alone do not replace
license obligations. Contributions are made under this project's MIT license.
