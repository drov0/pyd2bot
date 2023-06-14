import json
import os
import sqlite3

CURR_DIR = os.path.dirname(os.path.abspath(__file__))


class DofusPoiDB:
    DB_PATH = os.path.join(CURR_DIR, "poi_db.db")
    DEFAULT_EXPORT_FILE = os.path.join(CURR_DIR, "..", "..", "map_poi.json")
    
    def __init__(self):
        self.conn = sqlite3.connect(DofusPoiDB.DB_PATH)

    def close(self):
        self.conn.close()

    def insert_data_from_dict(self, data_dict):
        cursor = self.conn.cursor()

        # Inserting data into Maps_POIs
        for map_id, poi_ids in data_dict["map-pois"].items():
            for poi_id in poi_ids:
                cursor.execute(
                    "INSERT OR IGNORE INTO Maps_POIs (map_id, poi_id) VALUES (?, ?)",
                    (float(map_id), poi_id),
                )

        # Inserting data into ProcessedMaps
        for processed_map in data_dict["processed"]:
            x, y, direction = processed_map
            cursor.execute(
                "INSERT OR IGNORE INTO ProcessedMaps (map_id, x, y, direction) VALUES (?, ?, ?, ?)",
                (float(map_id), x, y, direction),
            )

        self.conn.commit()

    def add_pois_to_map(self, map_id, poi_ids):
        cursor = self.conn.cursor()

        # Add each POI to the Maps_POIs table
        for poi_id in poi_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO Maps_POIs (map_id, poi_id) VALUES (?, ?)",
                (float(map_id), int(poi_id)),
            )

        self.conn.commit()

    def add_processed_request(self, map_id, x, y, direction):
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "INSERT OR IGNORE INTO ProcessedMaps (map_id, x, y, direction) VALUES (?, ?, ?, ?)",
                (float(map_id), x, y, direction),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            print(f"Invalid direction value {direction} for map_id {map_id}.")

    def list_pois_of_map(self, map_id):
        cursor = self.conn.cursor()

        # Fetch the POIs associated with the given map_id
        cursor.execute(
            """
            SELECT poi_id
            FROM Maps_POIs
            WHERE map_id = ?;
        """,
            (map_id,),
        )

        pois = cursor.fetchall()
        poiIds = [poi[0] for poi in pois] if pois else []
        cursor.close()
        return poiIds
    
    def is_poi_present(self, map_id, poi_id):
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT * FROM Maps_POIs WHERE map_id = ? AND poi_id = ?",
            (float(map_id), int(poi_id)),
        )

        result = cursor.fetchone()
        cursor.close()
        if result is None:
            return False
        else:
            return True
        
    def is_query_processed(self, x, y, direction):
        cursor = self.conn.cursor()

        # Check if the given tuple [x, y, direction] exists in the ProcessedMaps table
        cursor.execute(
            """
            SELECT 1
            FROM ProcessedMaps
            WHERE x = ? AND y = ? AND direction = ?;
        """,
            (x, y, direction),
        )

        result = cursor.fetchone()
        cursor.close()
        return result

    def is_map_processed(self, x, y):
        cursor = self.conn.cursor()

        # Check if there are exactly four rows in the ProcessedMaps table with matching x and y and direction in [6, 2, 0, 4]
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM ProcessedMaps
            WHERE x = ? AND y = ? AND direction IN (6, 2, 0, 4)
            """,
            (x, y),
        )

        result = cursor.fetchone()
        cursor.close()

        # Check if the count of matching rows is equal to 4
        return result[0] == 4

    def is_map_exists(self, map_id):
        cursor = self.conn.cursor()

        # Check if the given map_id exists in the Maps_POIs table
        cursor.execute(
            """
            SELECT 1
            FROM Maps_POIs
            WHERE map_id = ?;
        """,
            (float(map_id),),
        )

        result = cursor.fetchone()
        cursor.close()
        return result

    def reset_processed_table(self):
        cursor = self.conn.cursor()

        # Delete all records from the ProcessedMaps table
        cursor.execute("DELETE FROM ProcessedMaps;")
        self.conn.commit()

        print("ProcessedMaps table has been reset.")

    def export_data(self, dest_file=None):
        if dest_file is None:
            dest_file = self.DEFAULT_EXPORT_FILE
            
        cursor = self.conn.cursor()

        # Fetch data from the Maps_POIs table
        cursor.execute("SELECT map_id, poi_id FROM Maps_POIs;")
        map_pois_data = cursor.fetchall()

        # Prepare the data dictionary
        map_pois = dict[str, list[int]]()

        # Populate the map-pois data
        for row in map_pois_data:
            map_id, poi_id = row
            map_id = str(int(map_id))  # Convert float to integer and then to string
            if map_id not in map_pois:
                map_pois[map_id] = []
            map_pois[map_id].append(poi_id)

        # Convert the data dictionary to JSON
        with open(dest_file, "w") as fp:
            json.dump(map_pois, fp, indent=2)
    
    def delete_map(self, map_id):
        cursor = self.conn.cursor()

        # Delete a specific map from the Maps_POIs table
        cursor.execute("DELETE FROM Maps_POIs WHERE map_id = ?;", (float(map_id),))
        self.conn.commit()

        print(f"Map with map_id {map_id} has been deleted.")

    def update_processed_map(self, map_id, x, y, direction):
        cursor = self.conn.cursor()

        try:
            # Update the ProcessedMaps table with the new values
            cursor.execute(
                "UPDATE ProcessedMaps SET x = ?, y = ?, direction = ? WHERE map_id = ?;",
                (x, y, direction, float(map_id)),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            print(f"Invalid direction value {direction} for map_id {map_id}.")

    def delete_processed_map(self, map_id):
        cursor = self.conn.cursor()

        # Delete a specific processed map from the ProcessedMaps table
        cursor.execute("DELETE FROM ProcessedMaps WHERE map_id = ?;", (float(map_id),))
        self.conn.commit()

        print(f"Processed map with map_id {map_id} has been deleted.")

if __name__ == "__main__":
    db = DofusPoiDB()
    db.reset_processed_table()
    db.export_data()
    pass
