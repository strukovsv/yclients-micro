from prometheus_client import Counter

API_YCLIENTS_POST_REQUEST_CNT = Counter(
    "api_yclients_post_request_cnt", "Count send post request to api yclients"
)
API_YCLIENTS_GET_REQUEST_CNT = Counter(
    "api_yclients_get_request_cnt", "Count send get request to api yclients"
)
API_YCLIENTS_DELETE_REQUEST_CNT = Counter(
    "api_yclients_delete_request_cnt",
    "Count send delete request to api yclients",
)
API_YCLIENTS_REQUEST_ERROR_CNT = Counter(
    "api_yclients_request_error_cnt", "Count error request to api yclients"
)

DO_EVENTS_CNT = Counter("do_events_cnt", "Count event receive from kafka")

WORKED_EVENTS_CNT = Counter(
    "worked_events_cnt", "Count worked event from kafka this"
)

PG_EXECUTE_CNT = Counter(
    "pg_execute_cnt", "Count executes postgres local base"
)

PG_FETCHALL_CNT = Counter(
    "pg_fetchall_cnt", "Count fetchalls postgres local base"
)

PG_UPDATES = Counter(
    "pg_updates",
    "Count update/insert/delete records postgres local base",
    ["method"],
)
