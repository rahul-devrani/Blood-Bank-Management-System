import sqlite3
import csv

DATABASE_NAME = 'blood_bank.db'
CSV_FILE_NAME = 'blood-banks.csv' 

COL_NAME = ' Blood Bank Name'
COL_ADDRESS = ' Address'
COL_CITY = ' City'
COL_STATE = ' State'

def load_data():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
    except sqlite3.OperationalError:
        print(f"ERROR: Database '{DATABASE_NAME}' not found.")
        print("Please run 'app.py' at least once to create the database file before running this script.")
        return

    cursor = conn.cursor()
    

    cursor.execute("DELETE FROM hospitals")
    print("Old hospital data cleared.")

    try:
       with open(CSV_FILE_NAME, mode='r', encoding='latin-1') as file:
            reader = csv.DictReader(file)
            
            count = 0
            for row in reader:
                try:
                    clean_row = {k.strip(): v for k, v in row.items()}
                    
                    name = clean_row.get(COL_NAME.strip())
                    address = clean_row.get(COL_ADDRESS.strip())
                    city = clean_row.get(COL_CITY.strip())
                    state = clean_row.get(COL_STATE.strip())
                    
                    if name and city and state:
                        cursor.execute(
                            "INSERT INTO hospitals (name, address, city, state) VALUES (?, ?, ?, ?)",
                            (name, address, city, state)
                        )
                        count += 1
                    else:
                        print(f"Skipping row, missing required data: {row}")

                except Exception as e:
                    print(f"Error inserting row: {e} | Data: {row}")

            conn.commit()
            print(f"Successfully loaded {count} hospitals into the database.")

    except FileNotFoundError:
        print(f"--- ERROR ---")
        print(f"File not found: '{CSV_FILE_NAME}'. Make sure it's in the same folder.")
    except Exception as e:
        print(f"--- ERROR ---")
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    print("Connecting to DB... (If this fails, run app.py first)")
    temp_conn = sqlite3.connect(DATABASE_NAME)
    temp_conn.close()
    
    load_data()