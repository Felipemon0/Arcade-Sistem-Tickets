import sqlite3

DB_NAME = "arcade.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            in_use REAL NOT NULL,
            reserve REAL NOT NULL,
            max_capacity REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storage (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            storage_blocks REAL NOT NULL,
            storage_boxes INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_name TEXT NOT NULL,
            action TEXT NOT NULL,
            amount REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM machines")
    if cursor.fetchone()[0] == 0:
        excel_machines = [
            ("Spindependence 1", 2.5, 2.0, 4.0),
            ("Spindependence 2", 1.8, 2.0, 4.0),
            ("Spindependence 3", 2.0, 2.0, 4.0),
            ("Spindependence 5", 2.0, 2.0, 4.0),
            ("Spindependence 4", 2.3, 2.0, 4.0),
            ("Plinko 1", 1.5, 1.0, 4.0),
            ("Plinko 2", 1.8, 1.0, 4.0),
            ("Plinko 3", 2.0, 1.0, 4.0),
            ("Plinko 4", 2.0, 1.0, 4.0),
            ("Plinko 5", 1.25, 1.0, 4.0),
            ("Plinko 6", 1.25, 1.0, 4.0),
            ("Wheel of fortune 1", 2.25, 2.0, 4.0),
            ("Wheel of fortune 2", 2.5, 2.0, 4.0),
            ("Wheel of fortune 3", 2.75, 2.0, 4.0),
            ("Wheel of fortune 4", 2.25, 2.0, 4.0),
            ("Jacks Hi 1", 1.25, 2.0, 4.0),
            ("Jacks Hi 2", 1.5, 2.0, 4.0),
            ("Jacks Hi 3", 1.25, 2.0, 4.0),
            ("Jacks Hi 4", 1.0, 2.0, 4.0),
            ("Jacks Hi 5", 1.5, 2.0, 4.0),
            ("Jacks Hi 6", 1.25, 2.0, 4.0),
            ("Doodle jump", 3.0, 3.0, 6.0),
            ("Monsterdrop mini 1", 9.0, 0.0, 12.0),
            ("Monsterdrop mini 2", 8.25, 0.0, 12.0),
            ("Red hot L", 5.5, 0.0, 10.0),
            ("Red hot R", 8.5, 0.0, 12.0),
            ("Pearl Fisher 1", 0.75, 1.0, 4.0),
            ("Pearl Fisher 2", 1.25, 3.0, 4.0),
            ("Pearl Fisher 3", 2.0, 3.0, 4.0),
            ("Smokin token L", 3.0, 0.0, 6.0),
            ("Smokin token R", 5.0, 0.0, 10.0),
            ("Big Bass R", 3.0, 0.0, 6.0),
            ("Scooby doo", 2.25, 0.0, 4.0),
            ("Big Bass L", 4.0, 0.0, 6.0),
            ("Ice ball 1", 2.25, 1.0, 4.0),
            ("Ice ball 2", 2.0, 1.0, 4.0),
            ("Ice ball 3", 1.8, 1.0, 4.0),
            ("Ice ball 4", 1.8, 1.0, 4.0),
            ("Ice ball 5", 1.5, 1.0, 4.0),
            ("Will Poker", 1.25, 1.0, 4.0),
            ("Deal or no Deal", 1.25, 3.0, 4.0),
            ("Connect 4", 3.75, 4.0, 6.0),
            ("Chameleon paradize", 2.75, 0.0, 4.0),
            ("Angry Birds 1", 0.75, 2.0, 4.0),
            ("Angry Birds 2", 0.75, 2.0, 4.0),
            ("Angry Birds 3", 0.25, 2.0, 4.0),
            ("Speed Demon", 3.75, 0.0, 6.0),
            ("Spin wheel", 1.0, 2.0, 4.0),
            ("Avengers L", 0.25, 4.0, 4.0),
            ("Avengers R", 0.75, 4.0, 4.0),
            ("Over the edge", 0.75, 1.0, 4.0),
            ("Monopoly", 2.5, 2.0, 4.0),
            ("Crazy tower", 3.75, 3.0, 6.0),
            ("Willy Wonka L", 3.5, 1.0, 6.0),
            ("Willy Wonka R", 3.0, 1.0, 6.0),
            ("Willy Crash", 1.0, 2.0, 4.0),
            ("Quik Drop", 1.25, 2.0, 4.0),
            ("Harpoon lagoon 1", 2.25, 0.0, 4.0),
            ("Harpoon lagoon 2", 1.25, 0.0, 4.0),
            ("Harpoon lagoon 3", 1.55, 0.0, 4.0),
            ("Harpoon lagoon 4", 1.5, 0.0, 4.0),
            ("Down the clown R", 1.6, 2.0, 4.0),
            ("Down the clown L", 1.25, 2.0, 4.0),
            ("Whack in Win", 3.55, 2.0, 6.0),
            ("Slush Rush L", 1.25, 1.0, 4.0),
            ("Slush Rush R", 1.6, 1.0, 4.0),
            ("Monsterdrop L", 7.8, 0.0, 12.0),
            ("Monsterdrop R", 7.5, 0.0, 12.0),
            ("Chaos Machine", 8.25, 0.0, 12.0),
            ("Open Box", 4.0, 6.0, 6.0),
        ]
        cursor.executemany(
            "INSERT INTO machines (name, in_use, reserve, max_capacity) VALUES (?, ?, ?, ?)",
            excel_machines
        )

    cursor.execute("SELECT COUNT(*) FROM storage")
    if cursor.fetchone()[0] == 0:
        # 7 boxes * 50 blocks/box = 350 blocks (matches Excel formula)
        cursor.execute(
            "INSERT INTO storage (id, storage_blocks, storage_boxes) VALUES (1, 350.0, 7)"
        )

    conn.commit()
    conn.close()
