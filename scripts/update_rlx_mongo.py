import requests
import json
import re
import time

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, date, timedelta, timezone
from pymongo import MongoClient, UpdateOne

from app.config import MONGO_URI


BASE_URL = "https://rlx.com.au"
SEARCH_URL = f"{BASE_URL}/umbraco/Surface/UmbracoSales/SalesSearch"

DATABASE_NAME = "theyarding"
COLLECTION_NAME = "sales_data"

# Normal daily operation:
# re-check the last 7 days so late/updated RLX reports are captured
DEFAULT_LOOKBACK_DAYS = 7

SALEYARD_MAP = {
    "CQLX": "Gracemere",
    "CTLX": "Carcoar",
    "CVLX": "Ballarat",
    "HRLX": "Singleton",
    "IRLX": "Inverell",
    "NVLX": "Barnawartha",
    "TRLX": "Tamworth",
    "SELX": "Yass",
    "GVLX": "Goulburn",
}

HEADERS = {
    "Accept": "*/*",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/141.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://rlx.com.au/",
}

session = requests.Session()


def rlx_date_text(d):
    return f"{d.day} {d.strftime('%b %Y')}"


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def upper_text(value):
    return clean_text(value).upper()


def number_to_string(value):
    if value is None:
        return ""
    return str(value)


def get_sale_round(description):
    if not description:
        return ""

    text = description.upper()

    if "PRIME" in text:
        return "PRIME"

    if "STORE" in text:
        return "STORE"

    if "WEANER" in text and "FEEDER" in text:
        return "WEANER AND FEEDER"

    if "WEANER" in text:
        return "WEANER"

    if "FEEDER" in text:
        return "FEEDER"

    return ""


def get_with_retry(
    url,
    params=None,
    headers=None,
    timeout=60,
    attempts=3,
):

    last_error = None

    for attempt in range(1, attempts + 1):

        try:
            response = session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )

            response.raise_for_status()
            return response

        except requests.RequestException as e:

            last_error = e

            print(
                f"Request failed "
                f"(attempt {attempt}/{attempts}): {e}"
            )

            if attempt < attempts:
                print("Waiting 5 seconds before retry...")
                time.sleep(5)

    raise last_error


def find_sales(start_date, end_date):

    params_base = {
        "hideSite": "False",
        "startDate": rlx_date_text(start_date),
        "startDate_submit": start_date.isoformat(),
        "endDate": rlx_date_text(end_date),
        "endDate_submit": end_date.isoformat(),
        "siteId": "0",
        "saleTypeId": "0",
        "speciesId": "0",
        "X-Requested-With": "XMLHttpRequest",
    }

    results = {}
    page = 1

    while True:

        print(f"Reading RLX search page {page}...")

        params = params_base.copy()
        params["pageNumber"] = page

        response = get_with_retry(
            SEARCH_URL,
            params=params,
            headers=HEADERS,
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        rows = soup.select(
            "table.e-sales-table tr"
        )

        current_date = None

        for row in rows:

            classes = row.get(
                "class",
                [],
            )

            if "e-sales-table__title-row" in classes:

                date_text = row.get_text(
                    " ",
                    strip=True,
                )

                try:
                    parsed = datetime.strptime(
                        date_text,
                        "%A %d %b %Y",
                    )

                    current_date = parsed.strftime(
                        "%Y-%m-%d"
                    )

                except ValueError:
                    current_date = None

                continue

            if "e-sales-table__body-row" not in classes:
                continue

            location_cell = row.select_one(
                '[data-js-table-col-header="Location"]'
            )

            type_cell = row.select_one(
                '[data-js-table-col-header="Species / Type"]'
            )

            qty_cell = row.select_one(
                '[data-js-table-col-header="Est. Qty"]'
            )

            description_cell = row.select_one(
                '[data-js-table-col-header="Description"]'
            )

            if not all([
                location_cell,
                type_cell,
                qty_cell,
                description_cell,
            ]):
                continue

            species_type = type_cell.get_text(
                " ",
                strip=True,
            )

            qty_text = qty_cell.get_text(
                " ",
                strip=True,
            )

            # Same discovery rules as historical scrape
            if species_type != "Saleyard Auction / Cattle":
                continue

            if not qty_text:
                continue

            link = None

            for candidate in row.find_all(
                "a",
                href=True,
            ):

                if candidate["href"].startswith(
                    "/sales/"
                ):
                    link = candidate
                    break

            if not link:
                continue

            sale_id = (
                link["href"]
                .split("/sales/")[1]
                .split("?")[0]
            )

            results[sale_id] = {
                "sale_id": sale_id,
                "sale_date": current_date,
                "location": location_cell.get_text(
                    " ",
                    strip=True,
                ),
                "description": description_cell.get_text(
                    " ",
                    strip=True,
                ),
                "url": urljoin(
                    BASE_URL,
                    link["href"],
                ),
            }

        pagination = soup.select_one(
            ".e-pagination__description"
        )

        if pagination:

            text = pagination.get_text(
                " ",
                strip=True,
            )

            try:
                total_pages = int(
                    text.split(" of ")[1]
                )
            except Exception:
                total_pages = page

        else:
            total_pages = page

        print(
            f"Page {page} of {total_pages}"
        )

        if page >= total_pages:
            break

        page += 1
        time.sleep(0.5)

    return sorted(
        results.values(),
        key=lambda x: (
            x["sale_date"] or "",
            x["location"],
            x["sale_id"],
        ),
    )


def download_sale(sale):

    response = get_with_retry(
        sale["url"],
        headers={
            "User-Agent":
                HEADERS["User-Agent"]
        },
    )

    match = re.search(
        r"var\s+saleData\s*=\s*(\{.*?\});",
        response.text,
        re.DOTALL,
    )

    if not match:
        raise Exception(
            f"Could not find saleData "
            f"for sale {sale['sale_id']}"
        )

    return json.loads(
        match.group(1)
    )


def transform_lot(
    sale,
    lot,
    now,
):

    description = sale.get(
        "description",
        "",
    )

    sale_round = get_sale_round(
        description
    )

    # Ignore special/private/stud/etc sales
    if not sale_round:
        return None, "unclassified"

    lot_status = clean_text(
        lot.get("LotStatus")
    )

    # Sold lots only
    if lot_status.upper() != "SOLD":
        return None, "unsold"

    breed = clean_text(
        lot.get("BreedName")
    )

    if not breed:
        return None, "blank_breed"

    sex = clean_text(
        lot.get("SexName")
    )

    if not sex:
        return None, "blank_sex"

    # IMPORTANT:
    # Store sales can legitimately have zero weight.
    # Do NOT apply the positive-weight rule to STORE.
    if sale_round != "STORE":

        try:
            average_weight = float(
                lot.get("AverageWeight")
                or 0
            )
        except (TypeError, ValueError):
            average_weight = 0

        try:
            total_weight = float(
                lot.get("TotalWeight")
                or 0
            )
        except (TypeError, ValueError):
            total_weight = 0

        if average_weight <= 0:
            return None, "zero_average_weight"

        if total_weight <= 0:
            return None, "zero_total_weight"

    location_code = sale[
        "location"
    ]

    saleyard_name = SALEYARD_MAP.get(
        location_code
    )

    if not saleyard_name:
        return None, f"unknown_saleyard:{location_code}"

    rlx_lot_id = lot.get("Id")

    if rlx_lot_id is None:
        return None, "missing_id"

    record = {
        "id": f"rlx_{rlx_lot_id}",
        "saleyard_name": saleyard_name,
        "sale_date": sale["sale_date"],
        "sale_round": sale_round,
        "hd": number_to_string(
            lot.get("Head")
        ),
        "unit_price": number_to_string(
            lot.get("UnitPrice")
        ),
        "total_weight": number_to_string(
            lot.get("TotalWeight")
        ),
        "average_weight": number_to_string(
            lot.get("AverageWeight")
        ),
        "age": "",
        "sex": upper_text(sex),
        "breed": upper_text(breed),
        "marks": "",
        "created_by": "RLX",
        "created_by_id": "rlx_import",
        "created_date": now,
        "updated_date": now,
        "is_sample": "false",
    }

    return record, None


def run_update(
    start_date=None,
    end_date=None,
):

    if end_date is None:
        end_date = date.today()

    if start_date is None:
        start_date = (
            end_date
            - timedelta(
                days=DEFAULT_LOOKBACK_DAYS
            )
        )

    print("=" * 70)
    print("THE YARDING - RLX INCREMENTAL UPDATE")
    print("=" * 70)

    print(
        f"Searching: "
        f"{start_date.isoformat()} "
        f"to "
        f"{end_date.isoformat()}"
    )

    # Establish RLX session
    get_with_retry(
        BASE_URL,
        headers=HEADERS,
        timeout=30,
    )

    sales = find_sales(
        start_date,
        end_date,
    )

    print()
    print(
        f"Qualifying RLX sales found: "
        f"{len(sales)}"
    )

    client = MongoClient(
        MONGO_URI
    )

    client.admin.command(
        "ping"
    )

    db = client[
        DATABASE_NAME
    ]

    collection = db[
        COLLECTION_NAME
    ]

    now = datetime.now(
        timezone.utc
    ).isoformat()

    stats = {
        "sales": len(sales),
        "lots_seen": 0,
        "records_ready": 0,
        "inserted": 0,
        "matched": 0,
        "modified": 0,
        "excluded": {},
        "download_errors": 0,
    }

    operations = []

    for i, sale in enumerate(
        sales,
        start=1,
    ):

        print(
            f"[{i}/{len(sales)}] "
            f"{sale['sale_date']} "
            f"{sale['location']} "
            f"{sale['description']}"
        )

        try:
            sale_data = download_sale(
                sale
            )

        except Exception as e:

            stats[
                "download_errors"
            ] += 1

            print(
                f"  ERROR: {e}"
            )

            continue

        lots = sale_data.get(
            "Lots",
            [],
        )

        print(
            f"  Lots: {len(lots)}"
        )

        for lot in lots:

            stats[
                "lots_seen"
            ] += 1

            record, reason = transform_lot(
                sale,
                lot,
                now,
            )

            if record is None:

                exclusions = stats[
                    "excluded"
                ]

                exclusions[reason] = (
                    exclusions.get(
                        reason,
                        0,
                    )
                    + 1
                )

                continue

            stats[
                "records_ready"
            ] += 1

            # Preserve original created_date
            # when an existing RLX record is updated.
            operations.append(
                UpdateOne(
                    {
                        "id":
                            record["id"]
                    },
                    {
                        "$set": {
                            k: v
                            for k, v
                            in record.items()
                            if k != "created_date"
                        },
                        "$setOnInsert": {
                            "created_date":
                                record[
                                    "created_date"
                                ]
                        },
                    },
                    upsert=True,
                )
            )

        # Write after each sale so memory stays low
        if operations:

            result = collection.bulk_write(
                operations,
                ordered=False,
            )

            stats["inserted"] += (
                result.upserted_count
            )

            stats["matched"] += (
                result.matched_count
            )

            stats["modified"] += (
                result.modified_count
            )

            operations = []

        # Be gentle to RLX
        time.sleep(1)

    print()
    print("=" * 70)
    print("UPDATE COMPLETE")
    print("=" * 70)

    print(
        f"Sales found:       "
        f"{stats['sales']:,}"
    )

    print(
        f"Download errors:   "
        f"{stats['download_errors']:,}"
    )

    print(
        f"Lots inspected:    "
        f"{stats['lots_seen']:,}"
    )

    print(
        f"Records processed: "
        f"{stats['records_ready']:,}"
    )

    print(
        f"New records:       "
        f"{stats['inserted']:,}"
    )

    print(
        f"Existing matched:  "
        f"{stats['matched']:,}"
    )

    print(
        f"Existing modified: "
        f"{stats['modified']:,}"
    )

    print()

    print("EXCLUSIONS")
    print("-" * 70)

    for reason, count in sorted(
        stats["excluded"].items()
    ):

        print(
            f"{reason:<30} "
            f"{count:>8,}"
        )

    print()
    print(
        f"Mongo sales_data count: "
        f"{collection.count_documents({}):,}"
    )

    print("=" * 70)

    client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start",
        help="Start date YYYY-MM-DD",
    )

    parser.add_argument(
        "--end",
        help="End date YYYY-MM-DD",
    )

    args = parser.parse_args()

    start = (
        date.fromisoformat(
            args.start
        )
        if args.start
        else None
    )

    end = (
        date.fromisoformat(
            args.end
        )
        if args.end
        else None
    )

    run_update(
        start_date=start,
        end_date=end,
    )
