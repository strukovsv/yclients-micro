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
    stages = []
    if kwarg.get("workflow") and kwarg.get("workflow_id"):
        stages = await select(
            "stages.sql",
            params={
                "workflow": kwarg.get("workflow"),
                "workflow_id": str(kwarg.get("workflow_id")),
            },
        )

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
            **{"stages": stages},
        }
    )
    logger.info(f"{result=}")
    return await render.to_text(template=template, **result)
