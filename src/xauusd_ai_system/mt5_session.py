from __future__ import annotations

from typing import Any


def initialize_mt5_session(
    mt5: Any,
    *,
    path: str | None = None,
    login: int | None = None,
    password: str | None = None,
    server: str | None = None,
) -> None:
    initialized = mt5.initialize(
        path=path,
        login=login,
        password=password,
        server=server,
    )
    if not initialized:
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    try:
        _login_if_supported(
            mt5,
            login=login,
            password=password,
            server=server,
        )
        _verify_account_binding(
            mt5,
            login=login,
            server=server,
        )
    except Exception:
        try:
            mt5.shutdown()
        except Exception:
            pass
        raise


def _login_if_supported(
    mt5: Any,
    *,
    login: int | None,
    password: str | None,
    server: str | None,
) -> None:
    expected_login = _normalize_login(login)
    if expected_login is None:
        return

    login_fn = getattr(mt5, "login", None)
    if login_fn is None:
        return

    login_kwargs: dict[str, Any] = {"login": expected_login}
    if password not in (None, ""):
        login_kwargs["password"] = password
    if server not in (None, ""):
        login_kwargs["server"] = server

    logged_in = bool(login_fn(**login_kwargs))
    if logged_in:
        return

    target = _format_target(login=expected_login, server=server)
    raise RuntimeError(f"MT5 login failed for {target}: {mt5.last_error()}")


def _verify_account_binding(
    mt5: Any,
    *,
    login: int | None,
    server: str | None,
) -> None:
    expected_login = _normalize_login(login)
    expected_server = _normalize_string(server)
    if expected_login is None and expected_server is None:
        return

    account_info_fn = getattr(mt5, "account_info", None)
    if account_info_fn is None:
        return

    account_info = account_info_fn()
    if account_info is None:
        raise RuntimeError(f"MT5 account_info failed after login: {mt5.last_error()}")

    actual_login = _normalize_login(getattr(account_info, "login", None))
    actual_server = _normalize_string(getattr(account_info, "server", None))

    if expected_login is not None and actual_login is not None and actual_login != expected_login:
        actual_target = _format_target(login=actual_login, server=actual_server)
        expected_target = _format_target(login=expected_login, server=expected_server)
        raise RuntimeError(
            f"MT5 connected to unexpected account {actual_target}; expected {expected_target}"
        )

    if (
        expected_server is not None
        and actual_server is not None
        and actual_server != expected_server
    ):
        actual_target = _format_target(login=actual_login, server=actual_server)
        expected_target = _format_target(login=expected_login, server=expected_server)
        raise RuntimeError(
            f"MT5 connected to unexpected server {actual_target}; expected {expected_target}"
        )


def _normalize_login(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _normalize_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _format_target(*, login: int | None, server: str | None) -> str:
    login_part = str(login) if login is not None else "<unknown-login>"
    server_part = server if server not in (None, "") else "<unknown-server>"
    return f"{login_part}@{server_part}"
