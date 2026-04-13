import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(
    Path.cwd() / "data" / "shipments.db"
    if (Path.cwd() / "data").exists()
    else PROJECT_ROOT / "data" / "shipments.db"
)
REQUIRED_FIELDS = ("shipment_id", "origin", "destination", "cost", "date")


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id TEXT PRIMARY KEY,
            origin TEXT,
            destination TEXT,
            cost REAL,
            date TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def insert_shipment(data):
    missing_fields = [field for field in REQUIRED_FIELDS if field not in data]
    if missing_fields:
        raise KeyError(f"Missing shipment fields: {', '.join(missing_fields)}")

    conn = _connect()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO shipments (shipment_id, origin, destination, cost, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["shipment_id"],
                data["origin"],
                data["destination"],
                data["cost"],
                data["date"],
            ),
        )
        conn.commit()
        return "Inserted"
    except sqlite3.IntegrityError:
        return "Duplicate"
    finally:
        conn.close()


def get_all_shipments():
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT shipment_id, origin, destination, cost, date FROM shipments")
    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "shipment_id": row[0],
            "origin": row[1],
            "destination": row[2],
            "cost": row[3],
            "date": row[4],
        }
        for row in rows
    ]
