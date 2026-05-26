from __future__ import annotations
from pydantic import Field
from datetime import date
from micro.models.header_event import HeaderEvent


class UpdatedClient(HeaderEvent):

    # fmt: off
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    # fmt: on

    def route_key(self):
        return self.client_id


class UpdatedLead(HeaderEvent):

    # fmt: off
    contact_id: str = Field(..., description="Идентификатор lead",)  # noqa
    # fmt: on

    def route_key(self):
        return self.contact_id


class ClientStatusChanged(HeaderEvent):

    # fmt: off
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    from_state: str | None = Field(None, description="Переход из статуса клиента",)  # noqa
    to_state: str = Field(..., description="Переход в статус клиента",)  # noqa
    # fmt: on

    def route_key(self):
        return self.client_id


class ClientTaskCreationRequested(HeaderEvent):
    """Создать задачу в CRM"""

    # fmt: off
    caption: str = Field(..., description="Название",)  # noqa
    status: str | None = Field(None, description="Статус задачи",)  # noqa
    start_date: date | None = Field(None, description="Дата начала задачи",)  # noqa
    end_date: date | None = Field(None, description="Дата завершения задачи",)  # noqa
    description: str = Field(..., description="Описание задачи",)  # noqa
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    priority: str | None = Field(None, description="Приоритет задачи",)  # noqa
    # fmt: on

    def route_key(self):
        return self.client_id
