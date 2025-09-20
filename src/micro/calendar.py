import logging
import asyncio

import caldav

import micro.config as config

from micro.singleton import MetaSingleton

logger = logging.getLogger(__name__)


class Calendar(metaclass=MetaSingleton):

    pool = None

    def __init__(self):
        logger.info("init caldav")

    async def get(self, calendar_name: str, date_from=None, date_to=None) -> list[dict]:

        def fill_event(component, calendar) -> dict[str, str]:
            # quite some data is tossed away here - like, the recurring rule.
            cur = {}
            cur["calendar"] = f"{calendar}"
            cur["summary"] = str(component.get("summary"))
            cur["description"] = str(component.get("description"))
            # month/day/year time? Never ever do that!
            # It's one of the most confusing date formats ever!
            # Use year-month-day time instead ... https://xkcd.com/1179/
            cur["start"] = component.start
            cur["end"] = component.end
            # For me the following line breaks because some imported calendar events
            # came without dtstamp.  But dtstamp is mandatory according to the RFC
            cur["datestamp"] = component.get("dtstamp").dt
            return cur

        def get_events():

            client = caldav.DAVClient(
                url=config.CALDAV_URL,
                username=config.CALDAV_USERNAME,
                password=config.CALDAV_TOKEN,
                timeout=60,
            )

            principal = client.principal()
            cal = principal.calendar(name=calendar_name)

            logger.info(f"Календарь: {cal.name=}")

            events = cal.date_search(
                start=date_from, end=date_to
            )

            result = []
            for event in events:
                # Most calendar events will have only one component,
                # and it can be accessed simply as event.component
                # The exception is special recurrences, to handle those
                # we may need to do the walk:
                for component in event.icalendar_instance.walk():
                    if component.name != "VEVENT":
                        continue
                    result.append(fill_event(component, cal))

            client.close()

            return result

        calendars = await asyncio.to_thread(get_events)
        return calendars
