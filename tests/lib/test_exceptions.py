import pytest

from core.lib.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BadRequest,
    ConflictError,
    InvalidData,
    InvalidForeignKey,
    LimitExceeded,
    NotFound,
    SuccessResponse,
    SuspiciousError,
)


class TestCustomExceptions:
    # Test InvalidData exception
    def test_invalid_data_exception_with_type(self):
        with pytest.raises(InvalidData) as exc_info:
            raise InvalidData(exception_type="Invalid data")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail[0]["type"] == "Invalid data"
        assert exc_info.value.headers is None

    def test_invalid_data_exception_with_type_msg(self):
        with pytest.raises(InvalidData) as exc_info:
            raise InvalidData(exception_type="Invalid data", msg="Invalid Data")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail[0]["type"] == "Invalid data"
        assert exc_info.value.detail[0]["msg"] == "Invalid Data"
        assert exc_info.value.headers is None

    def test_invalid_data_exception_with_type_loc(self):
        with pytest.raises(InvalidData) as exc_info:
            raise InvalidData(exception_type="Invalid data", loc="Location")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail[0]["type"] == "Invalid data"
        assert exc_info.value.detail[0]["loc"] == "Location"
        assert exc_info.value.headers is None

    def test_invalid_data_exception_with_type_msg_loc(self):
        with pytest.raises(InvalidData) as exc_info:
            raise InvalidData(
                exception_type="Invalid data", msg="Invalid Data", loc="Location"
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail[0]["type"] == "Invalid data"
        assert exc_info.value.detail[0]["msg"] == "Invalid Data"
        assert exc_info.value.detail[0]["loc"] == "Location"
        assert exc_info.value.headers is None

    # Test BadRequest exception
    def test_bad_request_exception(self):
        with pytest.raises(BadRequest) as exc_info:
            raise BadRequest(exception_type="Bad request")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail[0]["type"] == "Bad request"
        assert exc_info.value.headers is None

    # Test NotFound exception
    def test_not_found_exception(self):
        with pytest.raises(NotFound) as exc_info:
            raise NotFound(exception_type="Resource not found")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail[0]["type"] == "Resource not found"
        assert exc_info.value.headers is None

    # Test SuspiciousError exception
    def test_suspicious_error_exception(self):
        with pytest.raises(SuspiciousError) as exc_info:
            raise SuspiciousError(exception_type="This should not have happened.")

        assert exc_info.value.status_code == 510
        assert exc_info.value.detail[0]["type"] == "This should not have happened."
        assert exc_info.value.headers is None

    # Test Success Response
    def test_success_response(self):
        with pytest.raises(SuccessResponse) as exc_info:
            raise SuccessResponse(exception_type="Success")

        assert exc_info.value.status_code == 200
        assert exc_info.value.detail[0]["type"] == "Success"
        assert exc_info.value.headers is None

    # Test Limit Exceeded Exception
    def test_limit_exceeded(self):
        with pytest.raises(LimitExceeded) as exc_info:
            raise LimitExceeded(exception_type="Limit Exceeded")

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail[0]["type"] == "Limit Exceeded"
        assert exc_info.value.headers is None

    # Test Authenticatin Error
    def test_authentication_error(self):
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError(exception_type="Authentication Error")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail[0]["type"] == "Authentication Error"
        assert exc_info.value.headers is None

    # Test Authorization Error
    def test_authorization_error(self):
        with pytest.raises(AuthorizationError) as exc_info:
            raise AuthorizationError(exception_type="Authorization Error")

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail[0]["type"] == "Authorization Error"
        assert exc_info.value.headers is None

    # Test Conflict Error
    def test_conflict_error(self):
        with pytest.raises(ConflictError) as exc_info:
            raise ConflictError(exception_type="Conflict Error")

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail[0]["type"] == "Conflict Error"
        assert exc_info.value.headers is None

    # Test Invalid Foreign key
    def test_invalid_foreign_key_without_msg_type_table(self):
        with pytest.raises(InvalidForeignKey) as exc_info:
            raise InvalidForeignKey()

        expected_type = "integrity_error.invalid_foreign_key"
        expected_msg = "Invalid foreign key value"

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail[0]["type"] == expected_type
        assert exc_info.value.detail[0]["msg"] == expected_msg

    def test_invalid_foreign_key_without_msg_and_type_with_table(self):
        table = "test"
        with pytest.raises(InvalidForeignKey) as exc_info:
            raise InvalidForeignKey(table=table)

        expected_type = f"integrity_error.invalid_foreign_key.{table}"
        expected_msg = f"Invalid foreign key value for {table}"

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail[0]["type"] == expected_type
        assert exc_info.value.detail[0]["msg"] == expected_msg

    def test_invalid_foreign_key_with_msg_and_table_without_type(self):
        table = "test"
        message = f"The foreign key is not found in the table {table}."
        with pytest.raises(InvalidForeignKey) as exc_info:
            raise InvalidForeignKey(msg=message, table=table)

        expected_type = f"integrity_error.invalid_foreign_key.{table}"
        expected_msg = message

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail[0]["type"] == expected_type
        assert exc_info.value.detail[0]["msg"] == expected_msg

    def test_invalid_foreign_key_with_type_and_table_without_message(self):
        table = "test"
        exception_type = f"invalid_foreign_key_error_at_{table}"
        with pytest.raises(InvalidForeignKey) as exc_info:
            raise InvalidForeignKey(exception_type, table=table)

        expected_type = exception_type
        expected_msg = f"Invalid foreign key value for {table}"

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail[0]["type"] == expected_type
        assert exc_info.value.detail[0]["msg"] == expected_msg

    def test_invalid_foreign_key_with_type_table_and_message(self):
        table = "test"
        exception_type = f"invalid_foreign_key_error_at_{table}"
        message = f"The foreign key is not found in the table {table}."
        with pytest.raises(InvalidForeignKey) as exc_info:
            raise InvalidForeignKey(exception_type, msg=message, table=table)

        expected_type = exception_type
        expected_msg = message

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail[0]["type"] == expected_type
        assert exc_info.value.detail[0]["msg"] == expected_msg
