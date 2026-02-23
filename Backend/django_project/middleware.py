from django.http import JsonResponse
from django.conf import settings
import traceback
import logging

logger = logging.getLogger(__name__)


class CatchAllMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.info(
            "HTTP request",
            extra={
                "method": request.method,
                "path": request.path,
                "origin": request.META.get("HTTP_ORIGIN"),
            },
        )
        try:
            response = self.get_response(request)
        except Exception as e:
            if request.path.startswith("/api/") or request.method == "OPTIONS":
                raise
            data = {"error": "Fatal server error", "details": str(e)}
            if settings.DEBUG:
                data["trace"] = traceback.format_exc()
            logger.exception("Unhandled exception in CatchAllMiddleware")
            return JsonResponse(data, status=500)

        if request.path.startswith("/api/"):
            origin = request.META.get("HTTP_ORIGIN")
            allow_all = getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False)
            allowed_origins = set(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
            if origin and (allow_all or origin in allowed_origins):
                response["Access-Control-Allow-Origin"] = origin
                response["Vary"] = "Origin"
                response["Access-Control-Allow-Credentials"] = "true"
                response["Access-Control-Allow-Headers"] = (
                    "Authorization, Content-Type, X-CSRFToken"
                )
                response["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                )

            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if response.status_code == 401 and not auth_header:
                logger.warning(
                    "API request missing Authorization header",
                    extra={
                        "path": request.path,
                        "method": request.method,
                        "origin": origin,
                    },
                )

        return response
