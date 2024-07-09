import logging
from datetime import datetime
from fastapi import FastAPI, Request

from core.config import config
from services.onboarding.routes import app as onboarding_app
from services.authentication.routes import app as authentication_app


logger = logging.getLogger("uvicorn")

app = FastAPI(debug=config.debug)

app.mount("/authentication", authentication_app)
# app.mount("/notification", notification_app)
app.mount("/onboarding", onboarding_app)


# for r in authx_app.routes:
#     if r not in app.router.routes:
#         app.router.routes.append(r)

# for r in notification_app.routes:
#     if r not in app.router.routes:
#         app.router.routes.append(r)

# for r in onboarding_app.routes:
#     if r not in app.router.routes:
#         app.router.routes.append(r)

# for r in transaction_app.routes:
#     if r not in app.router.routes:
#         app.router.routes.append(r)


@app.get("/debug/")
def log_debug(request: Request):
    return {
        "debug": config.debug,
        "environment": config.environment,
        "scheme": request.url.scheme,
        "base_url": request.base_url,
        "current_time": datetime.now(),
    }
