import secrets

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from apps.core.config import get_settings
from apps.web.routers import articles, chat, digests, internal, sources

app = FastAPI(title="مجمّع أخبار الذكاء الاصطناعي")


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Gates every request behind HTTP Basic Auth when BASIC_AUTH_USERNAME
    and BASIC_AUTH_PASSWORD are both set — otherwise a no-op, so plain
    localhost development stays password-free. Meant for exposing the app
    beyond your own machine (e.g. a temporary public tunnel), not as a
    substitute for real auth in a multi-user deployment."""

    async def dispatch(self, request: Request, call_next):
        # A free external cron service triggers this route daily and can't
        # easily send Basic Auth credentials — RUN_DAILY_TOKEN in the query
        # string is that route's own auth mechanism instead (see
        # apps/web/routers/internal.py).
        if request.url.path == "/internal/run-daily":
            return await call_next(request)

        settings = get_settings()
        if not (settings.basic_auth_username and settings.basic_auth_password):
            return await call_next(request)

        header = request.headers.get("authorization")
        if header and header.startswith("Basic "):
            import base64

            try:
                decoded = base64.b64decode(header[len("Basic ") :]).decode("utf-8")
                username, _, password = decoded.partition(":")
            except Exception:
                username, password = "", ""

            valid_username = secrets.compare_digest(username, settings.basic_auth_username)
            valid_password = secrets.compare_digest(password, settings.basic_auth_password)
            if valid_username and valid_password:
                return await call_next(request)

        from starlette.responses import Response

        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="AI News"'},
        )


app.add_middleware(BasicAuthMiddleware)

app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")

app.include_router(sources.router)
app.include_router(articles.router)
app.include_router(digests.router)
app.include_router(chat.router)
app.include_router(internal.router)


@app.get("/")
def root():
    return RedirectResponse(url="/digests")
