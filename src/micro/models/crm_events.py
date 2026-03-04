from __future__ import annotations

from pydantic import Field

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
