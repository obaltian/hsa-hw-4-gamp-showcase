from __future__ import annotations

import argparse
import datetime
import http
import logging
import typing as tp

import google_measurement_protocol
import httpx
import pydantic

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push today's PLN-<currency> exchange rate to Google Analytics"
    )
    parser.add_argument("currency", help="foreign (non-PLN) currency code (e.g. USD)")
    parser.add_argument("--tracking-id", default="G-N68MP7FS00", help="tracking ID")
    parser.add_argument(
        "--client-id",
        default="72315d68-7130-43f4-b9bb-caead00a2483",
        help="client ID",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    logger.info(f"getting exchange rates for {args.currency}")
    exchange_rates = ExchangeRates.from_nbp(args.currency)
    if exchange_rates is None:
        logger.warning(f"no today's exchange rates are available for {args.currency}")
        return

    for rate in exchange_rates.rates:
        logger.info(f"got rate: {rate}")

        bid_event = google_measurement_protocol.event(
            "rates",
            f"{args.currency.lower()}_bid_rate_updated",
            label="Bid rate updated",
            value=rate.bid,
        )
        google_measurement_protocol.report(args.tracking_id, args.client_id, bid_event)
        logger.info(f"sent event: {bid_event}")

        ask_event = google_measurement_protocol.event(
            "rates",
            f"{args.currency.lower()}_ask_rate_updated",
            label="Ask rate updated",
            value=rate.ask,
        )
        google_measurement_protocol.report(args.tracking_id, args.client_id, ask_event)
        logger.info(f"sent event: {ask_event}")


class ExchangeRates(pydantic.BaseModel):
    currency: str
    currency_code: str
    rates: list[ExchangeRate]

    @classmethod
    def from_nbp(
        cls,
        pln_pair_currency: str = "usd",
        date: datetime.date = datetime.date.today(),
    ) -> tp.Self | None:
        """
        Instantiate ExchangeRates object based on data from NBP (National Bank of Poland).
        """
        nbp_response = httpx.get(
            f"http://api.nbp.pl/api/exchangerates/rates/c/{pln_pair_currency.lower()}/{date.isoformat()}/",
            params={"format": "json"},
        )
        try:
            nbp_response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code != http.HTTPStatus.NOT_FOUND:
                raise
            self = None
        else:
            self = cls(**nbp_response.json())
        return self


class ExchangeRate(pydantic.BaseModel):
    bid: float
    ask: float
    date: datetime.date


if __name__ == "__main__":
    main(parse_args())
