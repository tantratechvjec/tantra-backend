import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

cred = credentials.Certificate("tantra-3f498-firebase-adminsdk-fbsvc-02f7f4cd9e.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Add sample department
dept_ref = db.collection('departments').document('CSE001')
dept_ref.set({
    'name': 'Computer Science & Engineering',
    'description': 'Department of CSE focuses on software development and AI.',
    'logo_url': 'https://example.com/static/logos/cse_logo.png',
    'qr_url': 'https://example.com/static/qr/cse_qr.png',
    'created_at': datetime.utcnow()
})

# Add sample event
event_ref = db.collection('events').document('EVT001')
event_ref.set({
    'dept_id': 'CSE001',
    'name': 'Hackathon 2025',
    'description': '24-hour coding competition.',
    'date': '2025-10-10',
    'time': '09:00 AM',
    'venue': 'Main Auditorium',
    'image_url': 'https://example.com/static/event_images/hackathon.png',
    'payment_qr_url': 'https://example.com/static/qr/cse_qr.png',
    'created_at': datetime.utcnow()
})

# Add participants
participants = {
    'P001': {
        'name': 'Alice Johnson',
        'email': 'alice@example.com',
        'phone': '+91 9876543210',
        'college': 'Techno College',
        'branch': 'Computer Science',
        'year': '3rd Year'
    },
    'P002': {
        'name': 'Rahul Menon',
        'email': 'rahulmenon@gmail.com',
        'phone': '+91 9998877766',
        'college': 'Techno College',
        'branch': 'Electronics',
        'year': '2nd Year'
    }
}
for pid, pdata in participants.items():
    db.collection('participants').document(pid).set(pdata)

# Add registrations
db.collection('registrations').document('REG001').set({
    'participant_id': 'P001',
    'event_id': 'EVT001',
    'transaction_id': 'TXN123456'
})
db.collection('registrations').document('REG002').set({
    'participant_id': 'P002',
    'event_id': 'EVT001',
    'transaction_id': 'TXN789012'
})

print("✅ Sample data added successfully!")
