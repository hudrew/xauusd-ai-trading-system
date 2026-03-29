from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..config.schema import MarketDataConfig
from .base import MarketDataAdapter, Quote


class CTraderMarketDataAdapter(MarketDataAdapter):
    """
    cTrader market data adapter using Spotware's official Python SDK.

    Official docs specify:
    - application auth via `ProtoOAApplicationAuthReq`
    - account auth via `ProtoOAAccountAuthReq`
    - live quote subscription via `ProtoOASubscribeSpotsReq`
    - quote events via `ProtoOASpotEvent`
    """

    platform = "ctrader"

    def __init__(self, config: MarketDataConfig) -> None:
        self.config = config

    def get_latest_quote(self) -> Quote:
        try:
            from ctrader_open_api import Client, EndPoints, Prototobuf, TcpProtocol  # type: ignore  # noqa: F401
        except ImportError:
            # The real SDK import is validated in `_build_sdk_context`. This import
            # line is only here to fail fast for environments without the package.
            pass
        sdk = self._build_sdk_context()
        raise RuntimeError(
            "cTrader live quote retrieval requires an async runtime and active "
            "SDK callbacks. Use `build_spot_subscription_requests()` and the "
            "official Twisted event loop to consume ProtoOASpotEvent messages."
        )

    def get_recent_bars(self, count: int) -> list[dict[str, Any]]:
        raise RuntimeError(
            "Use cTrader historical trendbar/tick requests through the official "
            "Open API event loop. This adapter currently focuses on live spot flow."
        )

    def build_spot_subscription_requests(self) -> dict[str, Any]:
        client_id = self._required(self.config.ctrader.client_id, "client_id")
        client_secret = self._required(
            self.config.ctrader.client_secret,
            "client_secret",
        )
        account_id = self._required(self.config.ctrader.account_id, "account_id")
        access_token = self._required(
            self.config.ctrader.access_token,
            "access_token",
        )
        symbol_id = self._required(self.config.ctrader.symbol_id, "symbol_id")

        sdk = self._build_sdk_context()
        client = sdk["Client"](
            sdk["host"],
            sdk["EndPoints"].PROTOBUF_PORT,
            sdk["TcpProtocol"],
        )

        app_auth = sdk["ProtoOAApplicationAuthReq"]()
        app_auth.clientId = client_id
        app_auth.clientSecret = client_secret

        account_auth = sdk["ProtoOAAccountAuthReq"]()
        account_auth.ctidTraderAccountId = account_id
        account_auth.accessToken = access_token

        subscribe = sdk["ProtoOASubscribeSpotsReq"]()
        subscribe.ctidTraderAccountId = account_auth.ctidTraderAccountId
        subscribe.symbolId.append(symbol_id)
        subscribe.subscribeToSpotTimestamp = self.config.ctrader.subscribe_to_spot_timestamp

        return {
            "client": client,
            "application_auth_request": app_auth,
            "account_auth_request": account_auth,
            "subscribe_spots_request": subscribe,
            "symbol_name": self.config.ctrader.symbol_name,
        }

    @staticmethod
    def parse_spot_event(
        symbol: str,
        event: Any,
        *,
        digits: int = 2,
    ) -> Quote:
        bid = round(float(getattr(event, "bid", 0.0)) / 100000.0, digits)
        ask = round(float(getattr(event, "ask", 0.0)) / 100000.0, digits)
        timestamp = getattr(event, "timestamp", 0)
        if timestamp:
            point_in_time = datetime.fromtimestamp(timestamp / 1000.0, tz=timezone.utc)
        else:
            point_in_time = datetime.now(timezone.utc)
        return Quote(
            timestamp=point_in_time,
            symbol=symbol,
            bid=bid,
            ask=ask,
            metadata={"raw_timestamp": timestamp},
        )

    def _build_sdk_context(self) -> dict[str, Any]:
        try:
            from ctrader_open_api import Client, EndPoints, TcpProtocol
            from ctrader_open_api.messages.OpenApiMessages_pb2 import (
                ProtoOAAccountAuthReq,
                ProtoOAApplicationAuthReq,
                ProtoOASubscribeSpotsReq,
            )
        except ImportError as exc:
            raise RuntimeError(
                "ctrader-open-api is not installed. Install execution dependencies first."
            ) from exc

        host = (
            EndPoints.PROTOBUF_LIVE_HOST
            if self.config.ctrader.environment.lower() == "live"
            else EndPoints.PROTOBUF_DEMO_HOST
        )
        return {
            "Client": Client,
            "EndPoints": EndPoints,
            "TcpProtocol": TcpProtocol,
            "ProtoOAApplicationAuthReq": ProtoOAApplicationAuthReq,
            "ProtoOAAccountAuthReq": ProtoOAAccountAuthReq,
            "ProtoOASubscribeSpotsReq": ProtoOASubscribeSpotsReq,
            "host": host,
        }

    @staticmethod
    def _required(value: Any, field_name: str) -> Any:
        if value is None:
            raise ValueError(f"cTrader market data requires market_data.ctrader.{field_name}")
        return value
