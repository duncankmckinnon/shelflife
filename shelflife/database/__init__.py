from shelflife.config import IS_POSTGRES

if IS_POSTGRES:
    from shelflife.database._postgres import Base, async_session, engine, get_session
else:
    from shelflife.database._sqlite import Base, async_session, engine, get_session

__all__ = ["Base", "async_session", "engine", "get_session"]
