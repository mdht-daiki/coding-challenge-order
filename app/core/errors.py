from fastapi import HTTPException, status


class Conflict(HTTPException):
    def __init__(self, code: str, message: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": code, "message": message},
        )


class BadRequest(HTTPException):
    def __init__(self, code: str, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": code, "message": message},
        )


class NotFound(HTTPException):
    def __init__(self, code: str, message: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": code, "message": message},
        )
