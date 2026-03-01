from __future__ import annotations

import logging
import os

try:
    from micro.render_ext import to_text
except Exception:
    pass

from micro.pg_ext import fetchall
from micro.models.common_events import Report, InfoEvent


# Настройка логгера
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 🧩 Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────


async def send_manager(template: str, data: dict) -> None:
    """Отправить сообщение менеджерам."""
    message = await to_text(template=template, **data)
    await InfoEvent(text=message, acc="manager").send()
    # Продублируем пока сообщение администраторам
    await InfoEvent(text=message).send()


async def send_admin(template: str, data: dict) -> None:
    """Отправить сообщение менеджерам."""
    message = await to_text(template=template, **data)
    await InfoEvent(text=message).send()


async def send_channel(
    template: str,
    data: dict,
    channel: str,
    debug: bool,
):
    """Отправить сообщение в telegram chat (группу) или канал."""
    message = await to_text(template=template, **data)
    await Report(text=message).send(channel=channel)


async def send_client(template: str, data: dict, debug: bool = False) -> None:
    """Отправить сообщение клиенту."""
    message = await to_text(template=template, **data)
    client_id = data.get("client_id")
    if client_id:
        if debug:
            await InfoEvent(
                text=f"""Отправлено клиенту {client_id}:

    {message}"""
            ).send()
        else:
            # Отправляем клиенту
            await Report(text=message, plain=1).send(
                client_id=client_id,
            )
    else:
        await InfoEvent(
            text=f"""Не отправлено клиенту!!:

{message}"""
        ).send()


def template_exists(template_name: str) -> bool:
    """Проверяет, существует ли файл шаблона в папке templates."""
    full_path = os.path.join("templates", template_name)
    return os.path.isfile(
        full_path
    )  # isfile — точнее, чем exists (не пропустит папки)


async def send_stage_message(stage_id: int, debug: bool):
    for stage in await fetchall(
        """
select
  ws.*,
  w.moment,
  to_char(w.moment, 'DD.MM.YYYY HH24:MI:SS') start_date,
  to_char(ws.executed_at, 'DD.MM.YYYY HH24:MI:SS') executed_date
from workflow_stages ws
join workflow w on w.id = ws.workflow_id
where ws.id = %(id)s""",
        {"id": stage_id},
    ):
        # Отправить сообщение клиенту и администратору
        info = {
            "workflow": stage.get("workflow"),
            "capture_stage": stage.get("stage").lower(),
            "data": stage.get("data"),
            "start_date": stage.get("start_date"),
            "executed_date": stage.get("executed_date"),
        }
        data = {**stage.get("js"), **{"info": info}}
        logger.info(f"{data=}")
        await send_message(
            workflow=stage.get("workflow"),
            stage=stage.get("stage"),
            debug=debug,
            data=data,
        )


async def send_message(
    workflow: str, stage: str, data: dict, debug: bool = False
) -> None:
    """Отправить сообщения по шаблонам с постфиксами ролей и
    произвольными числовыми идентификаторами

    :param str workflow: имя workflow (каталог шаблонов)
    :param str stage: этап обработки (часть имени файла)
    :param dict  данные для рендеринга шаблона
    :param bool debug: включить режим отладки для клиентских шаблонов,
      defaults to False
    """
    for postfix in ["client", "manager", "admin", "attention"]:
        template = f"{workflow}/{stage}_{postfix}.txt".lower()
        if template_exists(template):
            senders = {
                "client": lambda t=template: send_client(
                    template=t, data=data, debug=debug
                ),
                "manager": lambda t=template: send_manager(
                    template=t, data=data
                ),
                "admin": lambda t=template: send_admin(template=t, data=data),
            }
            sender = senders.get(postfix)
            if sender:
                await sender()
                logger.info(f"send file {postfix}: {template}")
            else:
                await send_channel(
                    template=template,
                    data=data,
                    channel=postfix,
                    debug=False,
                )
                logger.info(
                    f"send file into channel {postfix}, file: {template}"
                )
