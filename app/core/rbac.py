from fastapi import HTTPException, status


ROLE_ACCESS = {
    "employee": ["employee_docs", "public_policies"],
    "manager": ["employee_docs", "public_policies", "manager_policies"],
    "hr": ["employee_docs", "public_policies", "manager_policies", "hr_docs"],
    "it": ["employee_docs", "public_policies", "it_docs"],
    "admin": ["*"]
}


def get_allowed_scopes(role: str) -> list[str]:
    return ROLE_ACCESS.get(role, [])


def enforce_scope(role: str, scope: str) -> None:
    allowed_scopes = get_allowed_scopes(role)
    if "*" in allowed_scopes:
        return
    if scope not in allowed_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this data.",
        )
