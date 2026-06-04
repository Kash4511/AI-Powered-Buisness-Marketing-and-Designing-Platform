from django.http import JsonResponse
from django.conf import settings
import traceback
import logging

logger = logging.getLogger(__name__)


class CatchAllMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
             logger.info(f"OPTIONS request from {request.META.get('HTTP_ORIGIN')} for {request.path}")
             
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
            # Use both META and headers for maximum compatibility
            origin = request.META.get("HTTP_ORIGIN") or request.headers.get("Origin")
            
            if origin:
                # Always reflect the origin if it exists to allow the browser to show the error
                response["Access-Control-Allow-Origin"] = origin
                response["Vary"] = "Origin"
                response["Access-Control-Allow-Credentials"] = "true"
                response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, Origin"
                
            return response

        return response
