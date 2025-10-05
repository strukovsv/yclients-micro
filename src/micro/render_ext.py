import logging

import micro.render as render
from micro.pg_ext import fetchone, fetchall, select
from micro.utils import hide_passwords, mask_phone_recursive

logger = logging.getLogger(__name__)


async def to_text(template: str, **kwarg) -> str:

    consts = hide_passwords(
        {
            row["name"]: row["template"]
            for row in await fetchall(
                """
select name, template from templates c"""
            )
        }
    )

    stage = {}
    if kwarg.get("stage_id"):
        for row in await select(
            "stages.sql",
            params={
                "stage_id": kwarg.get("stage_id"),
            },
        ):
            stage = row

    client = {}
    if kwarg.get("client_id"):
        for row in await select(
            "client-info.sql", params={"id": kwarg.get("client_id")}
        ):
            client = row

    result = mask_phone_recursive(
        {
            **kwarg,
            **{"client": client},
            **{"const": consts},
            **{"stage": stage},
        }
    )
    # logger.info(f"{result=}")
    return await render.to_text(template=template, **result)
