"""Làm việc với CSDL. Mọi file khác chỉ gọi query(), execute() và giao_dich()."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).parent / "database"
DB_PATH = FOLDER / "cuahang.db"


def duong_dan():
    # tests/ đặt DB_FILE để kiểm thử trên một bản CSDL riêng, không đụng dữ liệu thật
    return Path(os.environ.get("DB_FILE") or DB_PATH)


def hom_nay():
    """Ngày hôm nay. Test đặt HOM_NAY=2026-11-11 để kết quả không đổi theo ngày chạy."""
    v = os.environ.get("HOM_NAY")
    return date.fromisoformat(v) if v else date.today()


def tao_csdl(path=None):
    """Tạo (lại) CSDL từ schema.sql và seed.sql. Dữ liệu cũ bị xóa."""
    target_path = Path(path or duong_dan())
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_path, timeout=30.0)
    try:
        conn.executescript((FOLDER / "schema.sql").read_text(encoding="utf-8"))
        conn.executescript((FOLDER / "seed.sql").read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def get_conn():
    db_file = duong_dan()
    if not db_file.exists():  # chạy lần đầu (kể cả trên Streamlit Cloud) thì tự tạo CSDL
        tao_csdl()
    elif db_file == DB_PATH:
        # Tự động cập nhật nếu file schema.sql hoặc seed.sql được sửa mới hơn CSDL
        try:
            db_mtime = db_file.stat().st_mtime
            schema_file = FOLDER / "schema.sql"
            seed_file = FOLDER / "seed.sql"
            if schema_file.exists() and seed_file.exists():
                if schema_file.stat().st_mtime > db_mtime or seed_file.stat().st_mtime > db_mtime:
                    tao_csdl()
        except OSError:
            pass
    conn = sqlite3.connect(db_file, timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite mặc định tắt kiểm tra khóa ngoại
    return conn


def query(sql, params=()):
    """Chạy SELECT, trả về DataFrame."""
    conn = get_conn()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def execute(sql, params=()):
    """Chạy INSERT / UPDATE / DELETE, trả về id dòng vừa thêm."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


@contextmanager
def giao_dich():
    """Nhiều câu lệnh cùng thành công hoặc cùng bị hủy (lập hóa đơn vừa ghi phiếu vừa trừ kho)."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
