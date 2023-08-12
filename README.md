# hsa-hw-4-gamp-showcase

Basic project, pushing USD-PLN exchange rates to google analytics using GAMP.

## Send a request to google analytics

```sh
# install poetry
curl -sSL https://install.python-poetry.org | python3 -

poetry install
poetry run python push-to-ga.py usd API_SECRET
```
