import os
import sqlite3


CURR_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(CURR_DIR, "schema.sql")
DB_PATH = os.path.join(CURR_DIR, "poi_db.db") 


# Create a connection to the new database file
conn = sqlite3.connect(DB_PATH)

# Read the schema SQL from the file
with open(SCHEMA_PATH, 'r') as f:
    schema_sql = f.read()

# Execute the schema SQL to create the tables
conn.executescript(schema_sql)

# Commit the changes and close the connection
conn.commit()
conn.close()

print(f"The database file '{DB_PATH}' has been created with the schema from '{SCHEMA_PATH}'.")