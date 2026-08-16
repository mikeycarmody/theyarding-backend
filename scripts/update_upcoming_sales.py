import requests
import time
import hashlib

from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime, timezone
from pymongo import MongoClient

from app.config import MONGO_URI


BASE_URL = "https://rlx.com.au"
SEARCH_URL = f"{BASE_URL}/umbraco/Surface/UmbracoSales/SalesSearch"

DATABASE_NAME = "theyarding"
COLLECTION_NAME = "upcoming_sales"

DAYS_FORWARD = 7


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

    # Keep RLX codes as names for yards we have
    # not yet added to The Yarding.
    "WVLX": "WVLX",
    "EVLX": "EVLX",
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


def make_sale_id(
    sale_date,
    location_code,
    description,
):

    """
    Future RLX sales often don't yet have a /sales/<id>
    report link.

    Build a stable synthetic ID from the identifying fields.
    """

    raw = (
        f"{sale_date}|"
        f"{location_code}|"
        f"{description}"
    )

    digest = hashlib.sha1(
        raw.encode("utf-8")
    ).hexdigest()[:16]

    return f"upcoming_{digest}"


def find_upcoming_sales(
    start_date,
    end_date,
):

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

        print(f"Reading RLX page {page}...")

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

            # ---------------------------------------------
            # DATE HEADER
            # ---------------------------------------------

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

                    print(
                        f"Could not parse date: "
                        f"{date_text}"
                    )

                    current_date = None

                continue

            # ---------------------------------------------
            # NORMAL SALE ROW
            # ---------------------------------------------

            if "e-sales-table__body-row" not in classes:
                continue

            location_cell = row.select_one(
                '[data-js-table-col-header="Location"]'
            )

            type_cell = row.select_one(
                '[data-js-table-col-header="Species / Type"]'
            )

            description_cell = row.select_one(
                '[data-js-table-col-header="Description"]'
            )

            qty_cell = row.select_one(
                '[data-js-table-col-header="Est. Qty"]'
            )

            if not all([
                location_cell,
                type_cell,
                description_cell,
            ]):
                continue

            location_code = location_cell.get_text(
                " ",
                strip=True,
            )

            species_type = type_cell.get_text(
                " ",
                strip=True,
            )

            description = description_cell.get_text(
                " ",
                strip=True,
            )

            # ---------------------------------------------
            # CATTLE FILTER
            # ---------------------------------------------

            # Include ANY RLX row where Type / Species
            # contains "Cattle".
            if "CATTLE" not in species_type.upper():
                continue

            estimated_qty = ""

            if qty_cell:
                estimated_qty = qty_cell.get_text(
                    " ",
                    strip=True,
                )

            saleyard_name = SALEYARD_MAP.get(
                location_code,
                location_code,
            )

            # ---------------------------------------------
            # OPTIONAL RLX REPORT LINK
            # ---------------------------------------------

            report_url = ""
            rlx_sale_id = ""

            for link in row.find_all(
                "a",
                href=True,
            ):

                if link["href"].startswith(
                    "/sales/"
                ):

                    report_url = (
                        BASE_URL
                        + link["href"]
                    )

                    rlx_sale_id = (
                        link["href"]
                        .split("/sales/")[1]
                        .split("?")[0]
                    )

                    break

            # ---------------------------------------------
            # STABLE ID
            # ---------------------------------------------

            synthetic_id = make_sale_id(
                current_date,
                location_code,
                description,
            )

            results[synthetic_id] = {
                "id": synthetic_id,
                "rlx_sale_id": rlx_sale_id,
                "saleyard_name": saleyard_name,
                "location_code": location_code,
                "sale_date": current_date,
                "species_type": species_type,
                "description": description,
                "estimated_qty": estimated_qty,
                "rlx_url": report_url,
            }

        # ---------------------------------------------
        # PAGINATION
        # ---------------------------------------------

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
            x["saleyard_name"],
            x["description"],
        ),
    )


def main():

    start_date = date.today()

    end_date = (
        start_date
        + timedelta(
            days=DAYS_FORWARD
        )
    )

    print("=" * 70)
    print("THE YARDING - UPCOMING RLX SALES")
    print("=" * 70)

    print(
        f"Searching "
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

    sales = find_upcoming_sales(
        start_date,
        end_date,
    )

    now = datetime.now(
        timezone.utc
    ).isoformat()

    for sale in sales:
        sale["updated_date"] = now

    # ---------------------------------------------
    # MONGO
    # ---------------------------------------------

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

    # This collection represents the CURRENT
    # upcoming schedule, so replacing it each
    # day is intentional.
    collection.delete_many({})

    if sales:

        collection.insert_many(
            sales
        )

    # ---------------------------------------------
    # OUTPUT
    # ---------------------------------------------

    print()
    print("=" * 70)
    print("UPCOMING SALES UPDATED")
    print("=" * 70)

    print(
        f"Upcoming cattle sales: "
        f"{len(sales)}"
    )

    print()

    for sale in sales:

        qty = (
            sale["estimated_qty"]
            or "-"
        )

        print(
            f"{sale['sale_date']} | "
            f"{sale['location_code']:<5} | "
            f"{sale['saleyard_name']:<12} | "
            f"{qty:>8} | "
            f"{sale['description']}"
        )

    print()
    print(
        f"Mongo upcoming_sales count: "
        f"{collection.count_documents({})}"
    )

    print("=" * 70)

    client.close()


if __name__ == "__main__":
    main()
