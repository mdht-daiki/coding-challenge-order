from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def include_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Invalid request",
                "details": str(exc),
            },
        )

    @app.exception_handler(ValidationError)
    async def handle_pydantic_validation_error(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Invalid data",
                "details": str(exc),
            },
        )
