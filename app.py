from flask import Flask, render_template, request, redirect, jsonify, url_for
import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' 
load_dotenv()

# MySQL Connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        autocommit=True
)

db = get_db_connection()

def get_cursor():
    global db
    try:
        cursor = db.cursor(dictionary=True)
        return cursor
    except mysql.connector.Error:
        db = get_db_connection()  # Reconnect
        return db.cursor(dictionary=True)

# df fish base
df_fb = pd.read_csv("fish_data/fishbase_name_ids.csv").fillna("")
df_img = pd.read_csv("fish_data/fishbase_img.csv").fillna("")

# Create a dictionary mapping SpecCode to image URL for quick lookup
image_lookup = df_img.set_index('SpecCode')['PicPreferredName'].to_dict()


@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    searched = False
   

    # Fetch available tanks for dropdown and for display
    with db.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM tanks")  # Get all tank data
        tanks = cursor.fetchall()

        # Fetch mass_fish data
        cursor.execute("SELECT * FROM mass_fish")
        mass_fish = cursor.fetchall()
        
        # Fetch detail_fish data
        cursor.execute("SELECT * FROM detail_fish")
        detail_fish = cursor.fetchall()
    
    if request.method == 'POST':
        if request.form.get('action') == 'search':
            searched = True
            query = request.form.get('search', '').strip().lower()
            if query:
                # Get matching fish records
                matching_fish = df_fb[df_fb.apply(
                    lambda row: query in row['Genus'].lower() or
                                query in row['Species'].lower() or
                                query in row['FBname'].lower(),
                    axis=1
                )].to_dict('records')
                
                # Add image URLs to results
                for fish in matching_fish:
                    spec_code = fish['SpecCode']
                    fish['image_url'] = image_lookup.get(spec_code, '')
                    results.append(fish)
        elif request.form.get('action') == 'clear':
            results = []
            searched = False
   
    # Fetch reminders with tank names
    with db.cursor(dictionary=True) as cursor:
        cursor.execute("""
            SELECT r.reminder_id, r.tank_id, r.title, r.description, r.due_date, r.recurrence_type,
                r.priority, r.category, r.status, r.assigned_to, t.tank_name
            FROM reminders r
            JOIN tanks t ON r.tank_id = t.tank_id
        """)
        reminders = cursor.fetchall()
   
    return render_template('index.html',
                           results=results,
                           searched=searched,
                           tanks=tanks,
                           mass_fish=mass_fish,
                           detail_fish=detail_fish,
                           reminders=reminders,
                           show_tanks=True) # Flag to show tank section in template

@app.route('/add_mass_fish', methods=['POST'])
def add_mass_fish():
    try:
        tank_id = int(request.form['tank_id'])
        notes_mass = request.form['notes_mass']
        mass_quantity = int(request.form['mass_quantity'])
        avg_age_months = int(request.form['avg_age_months'])
        SpecCode = int(request.form['SpecCode'])
        
        cursor = db.cursor()
        sql = """
        INSERT INTO mass_fish 
        (tank_id, SpecCode, notes_mass, mass_quantity, avg_age_months) 
        VALUES (%s, %s, %s, %s, %s)
        """
        values = (tank_id, SpecCode, notes_mass, mass_quantity, avg_age_months)
        cursor.execute(sql, values)
        db.commit()
        cursor.close()
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error adding mass fish: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/add_detail_fish', methods=['POST'])
def add_detail_fish():
    try:
        tank_id = int(request.form['tank_id'])
        SpecCode = int(request.form['SpecCode'])
        notes_detail = request.form['notes_detail']
        avg_age_months = int(request.form['avg_age_months'])
        date_added = request.form['date_added']  # Date comes as string from form
        health_status = request.form['health_status']
        behavior_notes = request.form['behavior_notes']
        fish_name = request.form['fish_name']
        fish_identifiers = request.form['fish_identifiers']
       
        cursor = db.cursor()
        sql = """
        INSERT INTO detail_fish
        (tank_id, SpecCode, notes_detail, avg_age_months, date_added, health_status, behavior_notes, fish_name, fish_identifiers)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (tank_id, SpecCode, notes_detail, avg_age_months, date_added, health_status, behavior_notes, fish_name, fish_identifiers)
        cursor.execute(sql, values)
        db.commit()
        cursor.close()
       
        return redirect('/')  # Redirect back to the main page after adding
    except Exception as e:
        print(f"Error adding detail fish: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/add_tank', methods=['POST'])
def add_tank():
    tank_name = request.form['tank_name']
    fish_amount = request.form['fish_amount']
    water_type = request.form['water_type']
    water_amount_litre = request.form['water_amount_litre']
    tank_volume = request.form['tank_volume']
    filter_type = request.form['filter_type']
    heater = request.form['heater']
    temp_c = request.form['temp_c']
    last_cleaned = request.form['last_cleaned']
    cleaning_frequency_days = request.form['cleaning_frequency_days']
    lighting = request.form['lighting']
    location = request.form['location']

    cursor = db.cursor()
    sql = """
        INSERT INTO tanks (
            tank_name, fish_amount, water_type, water_amount_litre, tank_volume,
            filter_type, heater, temp_c, last_cleaned, cleaning_frequency_days,
            lighting, location
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        tank_name, fish_amount, water_type, water_amount_litre, tank_volume,
        filter_type, heater, temp_c, last_cleaned, cleaning_frequency_days,
        lighting, location
    )
    cursor.execute(sql, values)
    db.commit()
    cursor.close()

    return redirect('/')



@app.route('/delete_tank/<int:tank_id>', methods=['POST'])
def delete_tank(tank_id):
    cursor = db.cursor()
    
    # First delete related records in detail_fish table
    sql_detail = "DELETE FROM detail_fish WHERE tank_id = %s"
    cursor.execute(sql_detail, (tank_id,))
    
    # Delete related records in mass_fish table
    sql_mass = "DELETE FROM mass_fish WHERE tank_id = %s"
    cursor.execute(sql_mass, (tank_id,))
    
    # Delete related reminders
    sql_reminders = "DELETE FROM reminders WHERE tank_id = %s"
    cursor.execute(sql_reminders, (tank_id,))
    
    # Finally delete the tank itself
    sql_tank = "DELETE FROM tanks WHERE tank_id = %s"
    cursor.execute(sql_tank, (tank_id,))
    
    # Commit all changes
    db.commit()
    cursor.close()
    
    return redirect('/')


# kinda works
@app.route('/get_tank_data/<int:tank_id>', methods=['GET'])
def get_tank_data(tank_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tanks WHERE tank_id = %s", (tank_id,))
    tank = cursor.fetchone()
    cursor.close()
    
    if not tank:
        return jsonify({"error": "Tank not found"}), 404
    
    return jsonify(tank)


@app.route('/update_tank/<int:tank_id>', methods=['POST'])
def update_tank(tank_id):
    tank_name = request.form['tank_name']
    fish_amount = request.form['fish_amount']
    water_type = request.form['water_type']
    water_amount_litre = request.form['water_amount_litre']
    tank_volume = request.form['tank_volume']
    filter_type = request.form['filter_type']
    heater = request.form['heater']
    temp_c = request.form['temp_c']
    last_cleaned = request.form['last_cleaned']
    cleaning_frequency_days = request.form['cleaning_frequency_days']
    lighting = request.form['lighting']
    location = request.form['location']
    
    cursor = db.cursor()
    sql = """
        UPDATE tanks SET 
            tank_name = %s, 
            fish_amount = %s, 
            water_type = %s, 
            water_amount_litre = %s, 
            tank_volume = %s,
            filter_type = %s, 
            heater = %s, 
            temp_c = %s, 
            last_cleaned = %s, 
            cleaning_frequency_days = %s,
            lighting = %s, 
            location = %s
        WHERE tank_id = %s
    """
    values = (
        tank_name, fish_amount, water_type, water_amount_litre, tank_volume,
        filter_type, heater, temp_c, last_cleaned, cleaning_frequency_days,
        lighting, location, tank_id
    )
    cursor.execute(sql, values)
    db.commit()
    cursor.close()
    return redirect('/')

@app.route('/add_reminder', methods=['POST'])
def add_reminder():
    cursor = db.cursor()
    tank_id = request.form['tank_id']
    title = request.form['title']
    description = request.form.get('description', '')
    due_date = request.form['due_date']
    recurrence_type = request.form.get('recurrence_type', 'none')
    recurrence_interval = request.form.get('recurrence_interval')
    priority = request.form['priority']
    category = request.form['category']
    status = request.form['status']
    notification_time = request.form.get('notification_time', 0)
    assigned_to = request.form.get('assigned_to', None)
    
    completed_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Convert empty fields to None
    if not recurrence_interval:
        recurrence_interval = None
    if not assigned_to:
        assigned_to = None

    # SQL Query to insert data
    query = """
    INSERT INTO reminders (tank_id, title, description, completed_date, due_date, recurrence_type, 
    recurrence_interval, priority, category, status, notification_time, assigned_to) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (tank_id, title, description, completed_date, due_date, recurrence_type, recurrence_interval, 
              priority, category, status, notification_time, assigned_to)
    
    cursor.execute(query, values)
    db.commit()

    return redirect(url_for('index'))  # Redirect to home page



@app.route('/delete_reminder', methods=['POST'])
def delete_reminder():
    reminder_id = request.form['reminder_id']
    cursor = get_cursor()
    
    try:
        cursor.execute("DELETE FROM reminders WHERE reminder_id = %s", (reminder_id,))
        db.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        db.rollback()
    finally:
        cursor.close()
    
    return redirect(url_for('index'))


if __name__ == '__main__':
    db = get_db_connection()
    app.run(debug=True)
