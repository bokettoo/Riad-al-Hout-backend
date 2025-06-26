# Neptune's Bounty Backend

## Local Development: Quick Start

For local development convenience, you can now run the FastAPI backend directly with:

```bash
python main.py
```

This will automatically start a Uvicorn server with auto-reload enabled at http://127.0.0.1:8000.

> **Warning:**
>
> This method is for **local development only**. In production, you should use a proper ASGI server such as Uvicorn (optionally via Gunicorn) with a command like:
>
> ```bash
> uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
> ```
>
> Or, if deploying to Vercel or similar platforms, follow their specific deployment/build instructions.

## Why this change?

- The `python main.py` command is a convenience for local development and onboarding.
- It is **not** intended for production use, as it does not provide the robustness, performance, or security of a dedicated ASGI server.
- Always use the recommended deployment methods for staging/production environments. 