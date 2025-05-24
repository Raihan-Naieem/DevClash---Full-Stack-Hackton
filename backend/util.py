import sqlite3





def SQL(command, *placeholder):
    
    # Connect to the database (creates the database if it doesn't exist) and return rows as dictionaries
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    try:
        # Execute the command
        cursor.execute(command, placeholder)
        
        if command.strip().upper().startswith('SELECT'):
            # Fetch all rows for SELECT command and converts rows to a list of dictionaries
            rows = cursor.fetchall()
            result = [dict(row) for row in rows ]
            return result
        else:
            # Commit for non-SELECT commands (INSERT, UPDATE, DELETE)
            connection.commit()

    except sqlite3.IntegrityError as e: # Unique error
        raise ValueError(e)
    except sqlite3.Error as e:
        raise ValueError(e)
    finally:
        # Close the cursor and connection
        cursor.close()
        connection.close()