"""
View options for the History page: page size, status filter and sort order.

Kept free of Flask and database imports so it can be tested on its own.
"""

# Page sizes offered in the "Per page" menu. The largest is also the most the
# page will ever show, whatever is typed into the URL, because tables much past
# ~175 rows make the browser-side table sorting and rendering struggle.
PAGE_SIZES = (20, 50, 100, 150)

# Status filter values: query-string value -> label shown in the menu.
# "all" shows every job; the others match Job.status exactly.
STATUS_FILTERS = {
    "all": "All jobs",
    "fail": "Failed",
    "success": "Successful",
}

# Sort orders: query-string value -> label shown in the menu.
ORDERS = {
    "newest": "Newest first",
    "oldest": "Oldest first",
}


def get_view_options(args, database_limit):
    """
    Read the History page's view options from the query string, falling back
    to safe defaults for anything missing or invalid.

    :param args: request.args (a werkzeug MultiDict) or any mapping with .get()
    :param database_limit: the database_limit UI setting; lowers the cap if it
        is below the largest page size
    :return: dict with per_page, status, order, plus page_sizes for the menu
    """
    try:
        limit = int(database_limit)
    except (TypeError, ValueError):
        limit = PAGE_SIZES[-1]
    max_per_page = max(1, min(PAGE_SIZES[-1], limit))

    try:
        per_page = int(args.get("per_page", PAGE_SIZES[0]))
    except (TypeError, ValueError):
        per_page = PAGE_SIZES[0]
    per_page = max(1, min(per_page, max_per_page))

    status = args.get("status", "all")
    if status not in STATUS_FILTERS:
        status = "all"

    order = args.get("order", "newest")
    if order not in ORDERS:
        order = "newest"

    # Offer only the sizes the cap allows, plus the cap itself if it isn't one
    # of the standard sizes (for example database_limit set to 75).
    page_sizes = [size for size in PAGE_SIZES if size <= max_per_page]
    if max_per_page not in page_sizes:
        page_sizes.append(max_per_page)

    return {
        "per_page": per_page,
        "status": status,
        "order": order,
        "page_sizes": page_sizes,
    }
