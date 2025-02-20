# Errors and Exceptions

All error responses will be a dictionary with a root level `detail` key. The `detail` key can either be a string or an array of objects.

## Examples

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

```json
{
  "detail": [
    {
      "msg": "Resource not found",
      "type": "not_found"
    }
  ]
}
```

### Invalid email format for `email` in `POST` body

```json
"detail": [
    {
      "loc": [
        "body",
        "email"
      ],
      "msg": "Invalid email",
      "type": "value_error.email"
    }
  ]
```

### Invalid value for foreign key

```json
"detail": [
    {
      "msg": "Invalid key for country_id",
      "type": "integrity_error.invalid_foreign_key.country_id"
    }
  ]
```

### Session already exists

```json
"detail": [
    {
      "msg": "Session already exists",
      "type": "onboarding_error.session_already_exists"
    }
  ]
```

## Exception Classes

| Exception Class     | Status Code | Description                           |
| ------------------- | ----------- | ------------------------------------- |
| `InvalidSchema`     | 422         | Invalid data format or values in POST |
| `BadRequest`        | 400         | The requested data is not processable |
| `NotFound`          | 404         | Requested resource not found          |
| `InvalidForeignKey` | 400         | Invalid foreign key value sent        |
| `SuspiciousError`   | 510         | The request should not have sent      |

## Standard Error Types

| Error Type                            | Status Code | Description                         |
| ------------------------------------- | ----------- | ----------------------------------- |
| `not_found`                           | 404         | Resource not found                  |
| `value_error.email`                   | 400         | Invalid email format                |
| `value_error.empty`                   | 400         | Empty value                         |
| `value_error.int`                     | 400         | Invalid integer                     |
| `value_error.invalid`                 | 400         | Invalid value                       |
| `value_error.missing`                 | 400         | Missing value                       |
| `value_error.number.not_gt`           | 400         | Number not greater than             |
| `value_error.number.not_ge`           | 400         | Number not greater than or equal to |
| `value_error.number.not_lt`           | 400         | Number not less than                |
| `value_error.number.not_le`           | 400         | Number not less than or equal to    |
| `value_error.number.not_in_range`     | 400         | Number not in range                 |
| `value_error.str.min_length`          | 400         | String length too short             |
| `value_error.str.max_length`          | 400         | String length too long              |
| `value_error.str.not_in`              | 400         | String not in list                  |
| `value_error.str.regex`               | 400         | String does not match regex         |
| `integrity_error.invalid_foreign_key` | 400         | Invalid foreign key                 |
| `integrity_error.invalid_unique_key`  | 400         | Invalid unique key                  |

Notes

*   The `value_error` types are generated by [pydantic](https://pydantic-docs.helpmanual.io/usage/validators/).
*   The error types may be nested. For example, `value_error.int` is a child of `value_error`.
*   There may be custom nesting as well. For example, `integrity_error.invalid_foreign_key.country_id` is a child of `integrity_error.invalid_foreign_key`.

## Custom Error Type Examples

| Error Type                                             | Status Code | Description                                                    |
| ------------------------------------------------------ | ----------- | -------------------------------------------------------------- |
| `onboarding_error.session_already_exists`              | 400         | Session already exists.                                        |
| `onboarding_error.rejection_limit`                     | 429         | User has exceeded the maximum number of registration attempts. |
| `onboarding_error.pending_session_exists`              | 409         | User already has a pending registration.                       |
| `onboarding_error.invalid_otp`                         | 400         | OTP is invalid.                                                |
| `onboarding_error.otp_limit`                           | 429         | OTP tries limit is exceeded.                                   |
| `onboarding_error.otp_resend_limit_exceeded`           | 400         | Multiple OTP is requested within a minute.                     |
| `onboarding_error.otp_expired`                         | 400         | OTP is expired.                                                |
| `onboarding_error.mandatory_agreements`                | 422         | Not every mandatory ageements are accepted.                    |
| `onboarding_error.country_not_selected`                | 400         | Country is not selected in earlier stage.                      |
| `onboarding_error.card_not_selected`                   | 400         | Card is not selected in earlier stage.                         |
| `onboarding_error.id_exists`                           | 400         | ID number already exists.                                      |
| `onboarding_error.email_exists`                        | 400         | Email already exists.                                          |
| `onboarding_error.invalid_id`                          | 400         | ID number is invalid.                                          |
| `onboarding_error.invalid_dob`                         | 400         | Date of birth already exists.                                  |
| `onboarding_error.invalid_post_code`                   | 422         | Post code is invalid.                                          |
| `onboarding_error.bank_data_validation_failed`         | 400         | Provided data did not pass retail payment validation.          |
| `onboarding_error.bank_data_validation_limit_exceeded` | 429         | Retry limit for bank data validation has exceeded.             |
| `onboarding_error.identity_proof_already_retreived`    | 400         | Identity proof already retreived.                              |
| `onboarding_error.identity_validation_not_initiated`   | 400         | Identity validation not initiated yet.                         |
| `onboarding_error.try_again`                           | 400         | Idemia hasn't completed its verification process.              |
| `onboarding_error.invalid_card`                        | 422         | Submitted card is invalid.                                     |

For all custom error types, see [Custom Error Types](https://onboarding-service.up.railway.app/onboarding/get-error-description/).
