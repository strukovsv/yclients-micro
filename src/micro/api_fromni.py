import logging

import httpx

import micro.config as config
from micro.singleton import MetaSingleton

logger = logging.getLogger(__name__)


class FromniAuthError(Exception):
    """Ошибка авторизации в fromni"""


def is_auth_redirect(r: httpx.Response) -> bool:
    """Проверить, что ответ — редирект на авторизацию, а не данные

    :param httpx.Response r: ответ API мессенджера
    :return bool: True, если сессия мессенджера невалидна
    """
    # Протухшая sess выглядит как 302 на /authorize (при follow_redirects=False)
    # или как HTML вместо JSON. Ловим оба случая, чтобы не падать на r.json().
    return r.is_redirect or "application/json" not in r.headers.get(
        "content-type", ""
    )


class Fromni(metaclass=MetaSingleton):
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Ленивый общий клиент.

        Один на процесс: в его cookie jar живут connect.sid (auth) и sess (messenger),
        без этого OAuth-цепочку не пройти.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=config.FROMNI_TIMEOUT)
        return self._client

    async def signin(self) -> None:
        """Авторизоваться в SSO fromni и получить сессию мессенджера

        :raises FromniAuthError: fromni отклонил логин или OAuth не довёл до мессенджера
        """
        r = await self.client.post(
            config.FROMNI_SIGNIN_URL,  # https://api.auth.fromni.ru/signin
            json={
                "email": config.FROMNI_EMAIL,
                "password": config.FROMNI_PASSWORD,
            },
            headers={
                # Auth-сервер проверяет Origin, без него отвечает "CORS checking error"
                "Origin": config.FROMNI_AUTH_ORIGIN,  # https://auth.fromni.ru
                "Referer": f"{config.FROMNI_AUTH_ORIGIN}/",
            },
        )
        r.raise_for_status()
        data = r.json()
        if data.get("result") != "success":
            raise FromniAuthError(data.get("desc", "signin failed"))

        # Теперь в jar лежит connect.sid. Идём в мессенджер с редиректами:
        # messenger → /authorize (уйдёт connect.sid) → /callback?code → messenger ставит sess.
        r = await self.client.get(
            config.FROMNI_MESSENGER_URL, follow_redirects=True
        )
        logger.debug("fromni oauth chain: %s", [str(h.url) for h in r.history])

        # Если authorize показал consent-страницу вместо авто-редиректа,
        # цепочка закончится не на мессенджере. Это надо видеть явно, а не гадать.
        if r.url.host != httpx.URL(config.FROMNI_MESSENGER_URL).host:
            raise FromniAuthError(f"OAuth flow stopped at {r.url}")
        if "sess" not in self.client.cookies:
            raise FromniAuthError("messenger session cookie not set")
        logger.info("fromni: session established")

    async def messages(
        self, contact_id: str, limit: int = 20, offset: int = 0
    ) -> dict:
        """Получить сообщения контакта

        :param str contact_id: id контакта в fromni
        :param int limit: размер страницы, defaults to 20
        :param int offset: смещение, defaults to 0
        :raises FromniAuthError: не удалось получить сессию
        :return dict: ответ API мессенджера
        """
        payload = {
            "contactId": contact_id,
            "limit": limit,
            "order": [["id", "DESC"]],
            "offset": offset,
        }
        r = await self._post_messenger(
            "/api/user/messenger/contact/messages", payload
        )
        # Сессия протухла: перелогиниваемся один раз. Это не retry сети,
        # а штатное восстановление сессии, иначе сервис встанет после истечения sess.
        if is_auth_redirect(r):
            logger.info("fromni: session expired, re-signin")
            await self.signin()
            r = await self._post_messenger(
                "/api/user/messenger/contact/messages", payload
            )
            if is_auth_redirect(r):
                raise FromniAuthError("still unauthorized after signin")
        r.raise_for_status()
        return r.json()

    async def _post_messenger(
        self, path: str, payload: dict
    ) -> httpx.Response:
        """POST в API мессенджера без следования редиректам

        :param str path: путь API
        :param dict payload: тело запроса
        :return httpx.Response: сырой ответ
        """
        # follow_redirects=False намеренно: на POST 302 превратится в GET на /authorize,
        # и мы получим HTML логина вместо понятного сигнала "сессия умерла".
        return await self.client.post(
            f"{config.FROMNI_MESSENGER_URL}{path}",
            json=payload,
            headers={
                "Origin": config.FROMNI_MESSENGER_URL,  # https://messenger.fromni.ru
                "Referer": f"{config.FROMNI_MESSENGER_URL}/",
            },
            follow_redirects=False,
        )
