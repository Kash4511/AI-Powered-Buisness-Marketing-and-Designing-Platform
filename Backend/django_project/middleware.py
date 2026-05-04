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
            logger.exception("Unhandled exception in CatchAllMiddleware")
            data = {
                "success": False,
                "error": "Fatal server error",
                "details": str(e)
            }
            if settings.DEBUG:
                data["trace"] = traceback.format_exc()
            
            response = JsonResponse(data, status=500)
            
            # Ensure CORS headers are present even on fatal errors
            # Only add them if CorsMiddleware didn't already
            origin = request.META.get("HTTP_ORIGIN")
            if origin and not response.has_header("Access-Control-Allow-Origin"):
                response["Access-Control-Allow-Origin"] = origin
                response["Vary"] = "Origin"
                response["Access-Control-Allow-Credentials"] = "true"
            return response

        return response
