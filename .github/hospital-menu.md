# Hospital menu automation

The Hospital menu workflow checks the public hospital PDF at 09:00 Istanbul time on days 1, 2, and 3. It skips extraction when the current month is already published. A complete previous-month PDF is retried until day 3. An ambiguous or invalid transcription fails without a commit.

Add an OpenAI API project key as the repository Actions secret `OPENAI_API_KEY`. API access and billing are separate from a ChatGPT subscription. The optional repository variable `OPENAI_MENU_MODEL` overrides the default vision model, `gpt-4.1`; the replacement must support PDF input and structured outputs.

In Actions > Hospital menu > Run workflow, choose:

- `source` to check the live PDF download without an API key or a commit.
- `preview` to extract and validate the current PDF without a commit.
- `publish` to update the current month if it is not already published.

The scheduled run commits only `menus/hospital-menu-current.json` to `main`. Check failed runs under Actions and review the hospital PDF before making a manual correction. GitHub can disable schedules in public repositories after 60 days without repository activity.
