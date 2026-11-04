# Security boundaries

This is a local educational lab. It is not ready to host real customers or personal data.

- Keep the HTTP service on `127.0.0.1`. Docker Compose binds the published port to loopback.
- Only synthetic contacts are allowed. Email domains are validated, but a name field is still free text: do not enter real information.
- A generated local API key protects lab data. The browser keeps it in memory, never in URLs or localStorage. Do not share it.
- `.env`, databases, recordings, caches, and virtual environments are ignored by git and the Docker context.
- The base application has no external API integrations. Paid voice requires explicit opt-in and your own provider key. Audio then leaves your machine for the selected provider.
- SQL values are bound parameters. Dynamic page content uses `textContent`. The app sets a strict same-origin content security policy and checks Host headers.
- Tests block outbound socket connections and use temporary databases. Do not point tests at production storage.
- Public hosting would need separate user identity, authorization, rate and concurrency limits, HTTPS, retention rules, monitoring, and spend controls. Do not expose this local key model as a public service.

If you discover a vulnerability, do not include credentials, recordings, or contact details in a public issue. Use GitHub's private vulnerability reporting when enabled; otherwise contact the repository owner privately through a verified channel. Never paste a reproduction containing live secrets.
