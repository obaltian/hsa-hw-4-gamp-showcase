from __future__ import annotations

import argparse
import datetime
import http
import logging
import typing as tp

import httpx
import pydantic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push today's PLN-<currency> exchange rate to Google Analytics"
    )
    parser.add_argument("currency", help="foreign (non-PLN) currency code (e.g. USD)")
    parser.add_argument("api_secret", help="API secret")
    parser.add_argument("--measurement-id", default="G-N68MP7FS00", help="tracking ID")
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

    logger.info(f"sending {len(exchange_rates.rates)} events to Google Analytics")
    for rate in exchange_rates.rates:
        logger.info(f"{rate=}")
    httpx.post(
        "https://www.google-analytics.com/debug/mp/collect",
        params={"api_secret": args.api_secret, "measurement_id": args.measurement_id},
        json={
            "client_id": args.client_id,
            "events": [
                {
                    "name": f"{args.currency.lower()}_rate_update",
                    "params": {
                        "code": exchange_rates.code,
                        "date": rate.date.isoformat(),
                        "bid": rate.bid,
                        "ask": rate.ask,
                    },
                }
                for rate in exchange_rates.rates
            ],
        },
    )
    logger.info(f"sent {len(exchange_rates.rates)} events to Google Analytics")


class ExchangeRates(pydantic.BaseModel):
    currency: str
    code: str
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
    date: datetime.date = pydantic.Field(alias="effectiveDate")


if __name__ == "__main__":
    main(parse_args())
