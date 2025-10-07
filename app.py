from flask import Flask, render_template, request, redirect, url_for, send_file, Response
from pymongo import MongoClient
from bson.objectid import ObjectId # To handle MongoDB's default _id
from datetime import datetime
import io
import csv
from typing import List, Dict
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# -------------------- Upload folders --------------------
UPLOAD_QR_FOLDER = 'static/qr'
UPLOAD_EVENT_FOLDER = 'static/event_images'
UPLOAD_LOGO_FOLDER = 'static/logos'

os.makedirs(UPLOAD_QR_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_EVENT_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_LOGO_FOLDER, exist_ok=True)

app.config['UPLOAD_QR_FOLDER'] = UPLOAD_QR_FOLDER
app.config['UPLOAD_EVENT_FOLDER'] = UPLOAD_EVENT_FOLDER
app.config['UPLOAD_LOGO_FOLDER'] = UPLOAD_LOGO_FOLDER

# -------------------- MongoDB Connection --------------------
# Make sure your MongoDB server is running!
# -------------------- MongoDB Connection --------------------
client = MongoClient('mongodb+srv://tantratechvjec_db_user:pXgXUcv1hRjiiJQT@techfest-test.k3tvqia.mongodb.net/?retryWrites=true&w=majority&appName=techfest-test')
db = client['techfestdb'] # You can change 'techfestdb' if your database has a different name

# -------------------- Home --------------------
@app.route('/')
def index():
    return render_template('index.html')

# -------------------- Add Department --------------------
@app.route('/add_department', methods=['GET', 'POST'])
def add_department():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']

        # Upload logo
        logo_url = ""
        logo_file = request.files.get('logo_file')
        if logo_file and logo_file.filename != "":
            filename = secure_filename(logo_file.filename)
            path = os.path.join(app.config['UPLOAD_LOGO_FOLDER'], filename)
            logo_file.save(path)
            logo_url = url_for('static', filename=f'logos/{filename}', _external=True)

        # Upload QR
        qr_url = ""
        qr_file = request.files.get('qr_file')
        if qr_file and qr_file.filename != "":
            filename = secure_filename(qr_file.filename)
            path = os.path.join(app.config['UPLOAD_QR_FOLDER'], filename)
            qr_file.save(path)
            qr_url = url_for('static', filename=f'qr/{filename}', _external=True)

        db.departments.insert_one({
            'name': name,
            'description': description,
            'logo_url': logo_url,
            'qr_url': qr_url,
            'created_at': datetime.utcnow()
        })
        return redirect(url_for('index'))
    return render_template('add_department.html')

# -------------------- Add Event --------------------
@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    # Fetch departments to populate the dropdown
    departments_cursor = db.departments.find({}, {'name': 1})
    dept_list = [(str(dept['_id']), dept['name']) for dept in departments_cursor]

    if request.method == 'POST':
        dept_id = request.form['dept_id']
        name = request.form['name']
        description = request.form['description']
        date = request.form['date']
        time = request.form['time']
        venue = request.form['venue']

        # Event image upload
        image_url = ""
        event_file = request.files.get('event_image')
        if event_file and event_file.filename != "":
            filename = secure_filename(event_file.filename)
            path = os.path.join(app.config['UPLOAD_EVENT_FOLDER'], filename)
            event_file.save(path)
            image_url = url_for('static', filename=f'event_images/{filename}', _external=True)

        # Get department QR
        dept_doc = db.departments.find_one({'_id': ObjectId(dept_id)})
        payment_qr_url = ''
        if dept_doc:
            payment_qr_url = dept_doc.get('qr_url', '')

        db.events.insert_one({
            'dept_id': ObjectId(dept_id), # Store as ObjectId for referencing
            'name': name,
            'description': description,
            'date': date,
            'time': time,
            'venue': venue,
            'image_url': image_url,
            'payment_qr_url': payment_qr_url,
            'created_at': datetime.utcnow()
        })
        return redirect(url_for('index'))
    return render_template('add_event.html', departments=dept_list)
    
# -------------------- View Participants (Helper Function) --------------------
def _gather_participants(dept_id: str, event_id: str = None) -> List[Dict]:
    """Helper to collect participants using a MongoDB aggregation pipeline."""
    if not dept_id:
        return []

    # Stage 1: Match the events we are interested in
    match_stage = {'$match': {'dept_id': ObjectId(dept_id)}}
    if event_id:
        match_stage['$match']['_id'] = ObjectId(event_id)

    pipeline = [
        match_stage,
        # Stage 2: Join with registrations collection
        {
            '$lookup': {
                'from': 'registrations',
                'localField': '_id',
                'foreignField': 'event_id',
                'as': 'regs'
            }
        },
        # Stage 3: Deconstruct the regs array
        {'$unwind': '$regs'},
        # Stage 4: Join with participants collection
        {
            '$lookup': {
                'from': 'participants',
                'localField': 'regs.participant_id',
                'foreignField': '_id',
                'as': 'participant_info'
            }
        },
        # Stage 5: Deconstruct the participant_info array
        {'$unwind': '$participant_info'},
        # Stage 6: Project to shape the final output
        {
            '$project': {
                '_id': 0,
                'name': '$participant_info.name',
                'email': '$participant_info.email',
                'phone': '$participant_info.phone',
                'college': '$participant_info.college',
                'branch': '$participant_info.branch',
                'year': '$participant_info.year',
                'event_name': '$name',
                'event_id': '$_id',
                'transaction_id': '$regs.transaction_id'
            }
        }
    ]

    participants = list(db.events.aggregate(pipeline))
    return participants


# -------------------- View Participants (Route) --------------------
@app.route('/view_participants', methods=['GET'])
def view_participants():
    departments_cursor = db.departments.find({}, {'name': 1})
    dept_list = [(str(dept['_id']), dept['name']) for dept in departments_cursor]

    selected_dept_id = request.args.get('dept_id')
    selected_event_id = request.args.get('event_id')
    
    participants_info = []
    events_for_select = []

    if selected_dept_id:
        # Get all events for the selected department to populate the event dropdown
        events_cursor = db.events.find(
            {'dept_id': ObjectId(selected_dept_id)},
            {'name': 1}
        )
        events_for_select = [(str(e['_id']), e['name']) for e in events_cursor]
        
        # Fetch participants using the helper function
        participants_info = _gather_participants(selected_dept_id, selected_event_id)

    return render_template('view_participants.html',
                           departments=dept_list,
                           participants=participants_info,
                           selected_dept_id=selected_dept_id,
                           selected_event_id=selected_event_id,
                           events_for_select=events_for_select)


# -------------------- Export Participants --------------------
@app.route('/export_participants')
def export_participants():
    dept_id = request.args.get('dept_id')
    event_id = request.args.get('event_id')
    fmt = request.args.get('format', 'csv').lower()

    # The helper now efficiently gets data from MongoDB
    rows = _gather_participants(dept_id, event_id)
    if not rows:
        return "No participants found for the selected criteria.", 404

    headers = ['name', 'email', 'phone', 'college', 'branch', 'year', 'event_name', 'transaction_id']

    if fmt == 'xlsx':
        try:
            import pandas as pd
        except ImportError:
            return Response('pandas is required to export XLSX. Install with pip install pandas openpyxl', status=500)
        
        df = pd.DataFrame(rows)
        # Ensure all headers exist in the DataFrame
        for h in headers:
            if h not in df.columns:
                df[h] = ''
        df = df[headers] # Order columns correctly
        
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name='participants.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    if fmt == 'pdf':
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        except ImportError:
            return Response('reportlab is required to export PDF. Install with pip install reportlab', status=500)

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        data = [headers]
        for r in rows:
            data.append([r.get(h, '') for h in headers])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        doc.build([table])
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name='participants.pdf', mimetype='application/pdf')

    # Default: CSV
    si = io.StringIO()
    cw = csv.DictWriter(si, fieldnames=headers)
    cw.writeheader()
    cw.writerows(rows)
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=participants.csv"})

# -------------------- View Database Content --------------------
@app.route('/db_content')
def db_content():
    # Use an aggregation pipeline to fetch departments and their events in one query
    pipeline = [
        {
            '$lookup': {
                'from': 'events',
                'localField': '_id',
                'foreignField': 'dept_id',
                'as': 'events'
            }
        },
        {
            '$project': {
                'dept_name': '$name',
                'description': '$description',
                'logo_url': '$logo_url',
                'qr_url': '$qr_url',
                'events': '$events',
                'dept_id': '$_id'
            }
        }
    ]
    all_data_cursor = db.departments.aggregate(pipeline)

    # Convert ObjectId to string for JSON serialization in template if needed
    all_data = []
    for dept in all_data_cursor:
        dept['dept_id'] = str(dept['dept_id'])
        for event in dept['events']:
            event['_id'] = str(event['_id'])
            event['dept_id'] = str(event['dept_id'])
        all_data.append(dept)

    return render_template('db_content.html', data=all_data)

# -------------------- Run --------------------
if __name__ == '__main__':
    app.run(debug=True)