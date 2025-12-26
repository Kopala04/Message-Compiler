from message_hub.storage.db import DatabaseConfig, make_engine
from message_hub.storage.models import Base


def test_db_schema_create(tmp_path):
    cfg = DatabaseConfig(db_path=tmp_path / "test.sqlite")
    engine = make_engine(cfg)
    Base.metadata.create_all(engine)  # should not crash
