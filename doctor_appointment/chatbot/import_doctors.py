import csv
from chatbot.models import Doctor

file_path = 'chatbot/static/doctors_data.csv'
with open(file_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        doctor, created = Doctor.objects.update_or_create(
            name=row['name'],
            specialization=row['specialization'],
            location=row['location'],
            contact_number=row['contact_number'],
            available_days=row['available_days'],
            available_time=row['available_time'],
            url= row.get('url', '')
        )
        if created:
            print(f"Added doctor: {doctor.name}")
        else:
            print(f"Updated doctor: {doctor.name}")

# from chatbot.models import Doctor
# Doctor.objects.all().delete()