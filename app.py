from flask import Flask, render_template, request, redirect, jsonify, url_for
import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json


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


# Modify the index route to pass formatted reminders data to the template
# Modify the index route to also pass formatted reminders data
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
    
    # Get formatted reminders
    reminders = get_reminders()
    
    return render_template('index.html',
                          results=results,
                          searched=searched,
                          tanks=tanks,
                          mass_fish=mass_fish,
                          detail_fish=detail_fish,
                          reminders=reminders,
                          reminders_json=json.dumps(reminders, default=str),  # For calendar JavaScript
                          show_tanks=True)  # Flag to show tank section in template

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
        
        return redirect(url_for('index')) 
    except Exception as e:
        print(f"Error adding mass fish: {e}")
        return redirect(url_for('index')) 


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
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (tank_id, SpecCode, notes_detail, avg_age_months, date_added, health_status, behavior_notes, fish_name, fish_identifiers)
        cursor.execute(sql, values)
        db.commit()
        cursor.close()
       
        return redirect(url_for('index')) 
    except Exception as e:
        print(f"Error adding detail fish: {e}")
        return redirect(url_for('index'))
    
# Routes to get fish data
@app.route('/get_mass_fish/<int:id_mf>', methods=['GET'])
def get_mass_fish(id_mf):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM mass_fish WHERE id_mf = %s", (id_mf,))
    fish = cursor.fetchone()
    cursor.close()
    
    if not fish:
        return jsonify({"error": "Mass fish entry not found"}), 404
    
    return jsonify(fish)

@app.route('/get_detail_fish/<int:id_df>', methods=['GET'])
def get_detail_fish(id_df):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM detail_fish WHERE id_df = %s", (id_df,))
    fish = cursor.fetchone()
    cursor.close()
    
    if not fish:
        return jsonify({"error": "Detail fish entry not found"}), 404
    
    return jsonify(fish)

# Routes to update fish data
@app.route('/update_mass_fish/<int:id_mf>', methods=['POST'])
def update_mass_fish(id_mf):
    try:
        notes_mass = request.form['notes_mass']
        mass_quantity = int(request.form['mass_quantity'])
        avg_age_months = int(request.form['avg_age_months'])
        SpecCode = int(request.form['SpecCode'])
        
        cursor = db.cursor()
        sql = """
        UPDATE mass_fish SET
            SpecCode = %s,
            notes_mass = %s,
            mass_quantity = %s,
            avg_age_months = %s
        WHERE id_mf = %s
        """
        values = (SpecCode, notes_mass, mass_quantity, avg_age_months, id_mf)
        cursor.execute(sql, values)
        db.commit()
        cursor.close()
        
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error updating mass fish: {e}")
        return redirect(url_for('index'))

@app.route('/update_detail_fish/<int:id_df>', methods=['POST'])
def update_detail_fish(id_df):
    try:
        SpecCode = int(request.form['SpecCode'])
        notes_detail = request.form['notes_detail']
        avg_age_months = int(request.form['avg_age_months'])
        date_added = request.form['date_added']
        health_status = request.form['health_status']
        behavior_notes = request.form['behavior_notes']
        fish_name = request.form['fish_name']
        fish_identifiers = request.form['fish_identifiers']
        
        cursor = db.cursor()
        sql = """
        UPDATE detail_fish SET
            SpecCode = %s,
            notes_detail = %s,
            avg_age_months = %s,
            date_added = %s,
            health_status = %s,
            behavior_notes = %s,
            fish_name = %s,
            fish_identifiers = %s
        WHERE id_df = %s
        """
        values = (SpecCode, notes_detail, avg_age_months, date_added, health_status, 
                 behavior_notes, fish_name, fish_identifiers, id_df)
        cursor.execute(sql, values)
        db.commit()
        cursor.close()
        
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error updating detail fish: {e}")
        return redirect(url_for('index'))

# Routes to delete fish data
@app.route('/delete_mass_fish/<int:id_mf>', methods=['POST'])
def delete_mass_fish(id_mf):
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM mass_fish WHERE id_mf = %s", (id_mf,))
        db.commit()
        cursor.close()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error deleting mass fish: {e}")
        return redirect(url_for('index'))

@app.route('/delete_detail_fish/<int:id_df>', methods=['POST'])
def delete_detail_fish(id_df):
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM detail_fish WHERE id_df = %s", (id_df,))
        db.commit()
        cursor.close()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error deleting detail fish: {e}")
        return redirect(url_for('index'))

@app.route('/add_tank', methods=['POST'])
def add_tank():
    tank_name = request.form['tank_name']
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
            tank_name, water_type, water_amount_litre, tank_volume,
            filter_type, heater, temp_c, last_cleaned, cleaning_frequency_days,
            lighting, location
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        tank_name, water_type, water_amount_litre, tank_volume,
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
    
    try:
        # First delete related records in detail_fish table
        sql_detail = "DELETE FROM detail_fish WHERE tank_id = %s"
        cursor.execute(sql_detail, (tank_id,))
        
        # Delete related records in mass_fish table
        sql_mass = "DELETE FROM mass_fish WHERE tank_id = %s"
        cursor.execute(sql_mass, (tank_id,))
        
        # Find all reminder_ids associated with this tank
        cursor.execute("SELECT reminder_id FROM reminder_tanks WHERE tank_id = %s", (tank_id,))
        reminder_ids = cursor.fetchall()
        
        # Delete entries from reminder_tanks for this tank
        cursor.execute("DELETE FROM reminder_tanks WHERE tank_id = %s", (tank_id,))
        
        # Delete orphaned reminders (reminders that are no longer associated with any tank)
        for reminder in reminder_ids:
            reminder_id = reminder['reminder_id'] if isinstance(reminder, dict) else reminder[0]
            
            # Check if this reminder is still associated with any tank
            cursor.execute("SELECT COUNT(*) FROM reminder_tanks WHERE reminder_id = %s", (reminder_id,))
            count = cursor.fetchone()[0]
            
            # If not associated with any tank, delete the reminder
            if count == 0:
                cursor.execute("DELETE FROM reminders WHERE reminder_id = %s", (reminder_id,))
        
        # Finally delete the tank itself
        sql_tank = "DELETE FROM tanks WHERE tank_id = %s"
        cursor.execute(sql_tank, (tank_id,))
        
        # Commit all changes
        db.commit()
        
    except mysql.connector.Error as err:
        db.rollback()
        print(f"Error deleting tank: {err}")
        # You might want to flash an error message or handle this differently
    finally:
        cursor.close()
    
    return redirect('/')


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
        tank_name, water_type, water_amount_litre, tank_volume,
        filter_type, heater, temp_c, last_cleaned, cleaning_frequency_days,
        lighting, location, tank_id
    )
    cursor.execute(sql, values)
    db.commit()
    cursor.close()
    return redirect('/')


# Keep the existing route but modify it to return JSON for AJAX requests
@app.route('/add_reminder', methods=['POST'])
def add_reminder():
    title = request.form.get('title')
    description = request.form.get('description', '')
    due_date = request.form.get('due_date')
    start_date = request.form.get('start_date') or None
    recurrence_type = request.form.get('recurrence_type', 'none')
    recurrence_interval = request.form.getlist('recurrence_interval[]')
    recurrence_monthly = request.form.get('recurrence_monthly') or None
    category = request.form.get('category')
    status = request.form.get('status')
    tank_ids = request.form.getlist('tank_ids')
    
    # Prepare recurrence_interval as comma-separated string (if applicable)
    if recurrence_type == 'weekly':
        recurrence_interval_str = ','.join(recurrence_interval)
    else:
        recurrence_interval_str = None  # NULL in DB
        
    # Set recurrence_monthly if monthly, else None
    if recurrence_type != 'monthly':
        recurrence_monthly = None
        
    cursor = get_cursor()
    try:
        # Insert reminder
        sql = """
            INSERT INTO reminders
                (title, description, due_date, start_date, recurrence_type, recurrence_interval, recurrence_monthly, category, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            title, description, due_date, start_date,
            recurrence_type, recurrence_interval_str,
            recurrence_monthly, category, status
        ))
        reminder_id = cursor.lastrowid
        
        # Link to tanks
        for tank_id in tank_ids:
            cursor.execute("INSERT INTO reminder_tanks (reminder_id, tank_id) VALUES (%s, %s)", (reminder_id, tank_id))
        
        # Get tank names for the reminder
        tank_names = []
        if tank_ids:
            cursor.execute("""
                SELECT tank_name FROM tanks 
                WHERE tank_id IN ({})
            """.format(','.join(['%s'] * len(tank_ids))), tank_ids)
            tanks = cursor.fetchall()
            tank_names = [tank['tank_name'] for tank in tanks]
        
        db.commit()
        
        # If this is an AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Format dates for JSON
            due_date_iso = datetime.strptime(due_date, '%Y-%m-%dT%H:%M').isoformat() if due_date else None
            start_date_iso = datetime.strptime(start_date, '%Y-%m-%dT%H:%M').isoformat() if start_date else None
            
            # Return the reminder data
            return jsonify({
                'success': True,
                'reminder': {
                    'reminder_id': reminder_id,
                    'title': title,
                    'description': description,
                    'due_date': due_date,
                    'due_date_iso': due_date_iso,
                    'start_date': start_date,
                    'start_date_iso': start_date_iso,
                    'recurrence_type': recurrence_type,
                    'recurrence_interval': recurrence_interval_str,
                    'recurrence_monthly': recurrence_monthly,
                    'category': category,
                    'status': status,
                    'tank_names': ', '.join(tank_names)
                }
            })
        
        # For regular form submissions, redirect to home
        return redirect('/')
        
    except mysql.connector.Error as err:
        db.rollback()
        print(f"Error inserting reminder: {err}")
        
        # Handle AJAX errors
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'error': str(err)
            })
            
        return redirect('/')
        
    finally:
        cursor.close()

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


def get_color(category):
    """Return color code for reminder categories."""
    category_colors = {
        "Maintenance": "orange",
        "Water Change": "blue",
        "Feeding": "green",
        "Cleaning": "orange",
        "Medication": "red",
        "Testing": "purple",
        "General": "yellow"
    }
    return category_colors.get(category, "gray")

def get_reminders():
    """Fetch reminders from database."""
    with db.cursor(dictionary=True) as cursor:
        cursor.execute("""
            SELECT r.reminder_id, r.title, r.description, r.due_date, r.start_date,
                 r.recurrence_type, r.recurrence_interval, r.recurrence_monthly,
                 r.category, r.status,
                GROUP_CONCAT(t.tank_name SEPARATOR ', ') AS tank_names
            FROM reminders r
            LEFT JOIN reminder_tanks rt ON r.reminder_id = rt.reminder_id
            LEFT JOIN tanks t ON rt.tank_id = t.tank_id
            GROUP BY r.reminder_id
        """)
        reminders = cursor.fetchall()
        
        # Format dates for JavaScript
        formatted_reminders = []
        for reminder in reminders:
            formatted_reminder = {
                'reminder_id': reminder['reminder_id'],
                'title': reminder['title'],
                'description': reminder['description'],
                'eventName': reminder['title'],  # For calendar compatibility
                'category': reminder['category'],
                'status': reminder['status'],
                'tank_names': reminder['tank_names'],
                'color': get_color(reminder['category'])
            }
            
            # Format due date for JavaScript
            if reminder['due_date']:
                formatted_reminder['due_date_iso'] = reminder['due_date'].isoformat()
                formatted_reminder['date'] = reminder['due_date'].isoformat()  # For calendar compatibility
            
            # Format start date if available
            if reminder['start_date']:
                formatted_reminder['start_date_iso'] = reminder['start_date'].isoformat()
            
            formatted_reminders.append(formatted_reminder)
    
    return formatted_reminders

@app.route('/calendar')
def calendar_view():
    """Dedicated calendar view page."""
    reminders = get_reminders()
    
    return render_template(
        "calendar.html",
        reminders=reminders,
        reminders_json=json.dumps(reminders, default=str)  # Handle date serialization
    )


if __name__ == '__main__':
    db = get_db_connection()
    app.run(debug=True)
