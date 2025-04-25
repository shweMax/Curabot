from django.http import JsonResponse
from django.shortcuts import render, redirect
import requests
from .models import Doctor
import logging
from googletrans import Translator
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.views.decorators.csrf import csrf_exempt
import json
import os
from django.conf import settings
from django.core.mail import send_mail
from .models import Prescription
from .forms import PrescriptionUploadForm
import pytesseract
from PIL import Image
from PyPDF2 import PdfReader

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logger = logging.getLogger(__name__)

CALENDLY_TOKEN = "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzMxMzIwNTY1LCJqdGkiOiJhODgzZGZmMi1lMDU5LTRlODQtYjEzMi1kZGFkNjc1N2M5NzMiLCJ1c2VyX3V1aWQiOiJlOTdkYTcwYy0xZTVhLTQ1NGEtYjgxOC0zMjc3ODE5NDRiZGIifQ.XqrygphnkvkmTuQqScOL9b2kDk7rKe2UaUQmoLc1wS0imqjxoIgfXRfw_r__Kk1ZQ0Jr_TYUTFESqe_R1RELOw.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzMxMjE2OTA2LCJqdGkiOiI0ZWM3YWI2Zi02MmNmLTQ0YTAtOWIyMC0wNzYwMjI5Y2M4NDciLCJ1c2VyX3V1aWQiOiJlOTdkYTcwYy0xZTVhLTQ1NGEtYjgxOC0zMjc3ODE5NDRiZGIifQ.ISyLwVytSiadsa3lg1BIdzQR98XNjesTHQ0CSeqOwRje5nfrsQVc4iLmGrEIBt05hoQ_g_iO0_Q0_TbzeCHTRg"  # Use your copied token
CALENDLY_USER = "dshwe1298"  # Your Calendly username or handle
CALENDLY_EVENT_TYPE = "doctor-s-consultation"  # Event type name you created on Calendly

def home(request):
    return render(request, 'chatbot/sample.html')

def book_appointment(request):
    return render(request, 'chatbot/index.html')

def get_available_times(request):
    headers = {'Authorization': f'Bearer {CALENDLY_TOKEN}'}
    url = f'https://api.calendly.com/scheduling/availability?user={CALENDLY_USER}&event_type={CALENDLY_EVENT_TYPE}'
    try:
        logger.info(f"Making request to Calendly API: {url}")
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            available_times = response.json().get('data', [])
            times_list = [time['start'] for time in available_times]
            return JsonResponse({'available_times': times_list})
        else:
            return JsonResponse({'error': 'Failed to fetch data from Calendly', 'details': response.text}, status=500)
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def schedule_appointment(request):
    calendly_link = "https://calendly.com/dshwe1298/doctor-s-consultation"
    return redirect(calendly_link)

def doctors_list(request):
    doctors = Doctor.objects.all()
    return render(request, 'chatbot/doctors_list.html', {'doctors': doctors})

def get_doctors(request):
    doctors = Doctor.objects.all()
    data = {
        'doctors': [
            {
                'id': doctor.id,
                'name': doctor.name,
                'specialization': doctor.specialization,
                'location': doctor.location,
                'contact_number': doctor.contact_number,
                'availability_days': doctor.available_days,
                'available_time': doctor.available_time,
                'url': doctor.url
            }
            for doctor in doctors
        ]
    }
    return JsonResponse(data)

def check_availability(request):
    doctor_id = request.GET.get('doctor_id')
    try:
        doctor = Doctor.objects.get(id=doctor_id)
        data = {
            'available_times': f"{doctor.available_days} - {doctor.available_time}",
            'doctor_name': doctor.name,
            'doctor_specialization': doctor.specialization,
            'url': doctor.url
        }
        return JsonResponse(data)
    except Doctor.DoesNotExist:
        return JsonResponse({'error': 'Doctor not found'}, status=404)
    
# Function to translate Hindi text to English
def translate_text(text, from_lang='hi', to_lang='en'):
    # Check if the text is empty
    if not text.strip():
        print("No text provided for translation.")
        return None

    try:
        # Initialize the translator object only once
        translator = Translator()

        # If the text is already in the target language, no need to translate
        if from_lang == to_lang:
            return text

        # Translate the text
        translated = translator.translate(text, src=from_lang, dest=to_lang)
        
        # Debugging print statements for tracking translation process
        print(f"Original text: {text}")
        print(f"Translated text: {translated.text}")
        
        return translated.text
    except Exception as e:
        print(f"Translation error: {e}")
        return None

# View to handle translation requests
@csrf_exempt
def translate_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text', '')
            from_lang = data.get('from_lang', 'hi')  # Default is Hindi
            to_lang = data.get('to_lang', 'en')  # Default is English

            # Debug log to track translation requests
            print(f"Translating from {from_lang} to {to_lang}: {text}")

            # Translate text
            translated_text = translate_text(text, from_lang, to_lang)
            if translated_text:
                return JsonResponse({'translated_text': translated_text})
            else:
                return JsonResponse({'error': 'Translation failed'}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

# Function to send email via SMTP (using Django’s send_mail)
def send_email(user_name, original_text, translated_text, sender_email, sender_password, receiver_email):
    msg = MIMEMultipart("alternative")
    msg['Subject'] = f'Translation Result for {user_name}'
    msg['From'] = sender_email
    msg['To'] = receiver_email

    # Create the HTML content with better formatting
    html_content = f"""
    <html>
    <body>
        <p><strong>Patient Name:</strong> {user_name}</p>
        <p><strong>Original Text (Hindi):</strong> {original_text}</p>
        <p><strong>Translated Text (English):</strong> {translated_text}</p>
    </body>
    </html>
    """

    # Attach the HTML content to the email
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
# View to handle sending email with translated symptoms
@csrf_exempt
def send_email_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        original_text = data.get('symptoms', '')
        user_name = data.get('user_name', 'Patient')
        # print(f"Original symptoms text: {original_text}")
        
        # Translate the symptoms from Hindi to English (or another language)
        translated_text = translate_text(original_text, from_lang='hi', to_lang='en')  # Assuming Hindi to English translation

        if translated_text:  # If translation is successful
            sender_email = settings.EMAIL_HOST_USER  # Get the email from settings
            sender_password = settings.EMAIL_HOST_PASSWORD  # Your app password or regular password
            receiver_email = "dshwe1298@gmail.com"  # Replace with actual doctor's email

            # Send email using the send_email function
            if send_email(user_name, original_text, translated_text, sender_email, sender_password, receiver_email):
                return JsonResponse({'message': 'Email sent successfully!'})
            else:
                return JsonResponse({'error': 'Failed to send email'}, status=500)
        else:
            return JsonResponse({'error': 'Translation failed'}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def upload_prescription(request):
    if request.method == 'POST':
        form = PrescriptionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            prescription = form.save()
            file_path = prescription.file.path
            extracted_text = extract_text_from_file(file_path)
            # Simulate recommendations based on the uploaded prescription
            recommendations = recommend_medicine(extracted_text)
            return JsonResponse({
                'success': True,
                'message': 'File uploaded successfully!',
                'file_name': prescription.file.name,
                'recommendations': recommendations,
            })
        return JsonResponse({'success': False, 'message': 'Invalid file.'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

def extract_text_from_file(file_path):
    file_extension = os.path.splitext(file_path)[1].lower()
    
    # Check if the file is an image or a PDF
    if file_extension in ['.png', '.jpg', '.jpeg']:
        return extract_text_from_image(file_path)
    elif file_extension == '.pdf':
        return extract_text_from_pdf(file_path)
    else:
        return "Unsupported file format"

def extract_text_from_image(image_path):
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text

def extract_text_from_pdf(pdf_path):
    text = ''
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)
        # Iterate through the pages and extract text
        for page in reader.pages:
            text += page.extract_text()
    return text

def recommend_medicine(extracted_text):
    # Simple logic to recommend medicine based on keywords in extracted text
    # This can be expanded with a real database or API lookup
    medicines = []

    if "paracetamol" in extracted_text:
        medicines.append("Paracetamol 500mg - Take 1 tablet twice daily after meals.")
    
    # Condition for Cough Syrup
    if "cough" in extracted_text:
        medicines.append("Corex Cough Syrup - 5ml twice daily.")

    # Condition for antibiotics (e.g., Amoxicillin)
    if "amoxicillin" in extracted_text or "antibiotic" in extracted_text:
        medicines.append("Amoxicillin 500mg - Take 1 capsule every 8 hours for 7 days.")

    # Condition for pain relief (e.g., Ibuprofen)
    if "ibuprofen" in extracted_text or "pain" in extracted_text:
        medicines.append("Ibuprofen 400mg - Take 1 tablet every 6-8 hours as needed for pain.")

    # Condition for fever (e.g., Acetaminophen)
    if "fever" in extracted_text or "acetaminophen" in extracted_text:
        medicines.append("Acetaminophen 500mg - Take 1 tablet every 4-6 hours for fever.")

    # Condition for diabetes (e.g., Metformin)
    if "diabetes" in extracted_text or "metformin" in extracted_text:
        medicines.append("Metformin 500mg - Take 1 tablet twice daily with meals.")

    # Condition for hypertension (e.g., Amlodipine)
    if "blood pressure" in extracted_text or "hypertension" in extracted_text or "amlodipine" in extracted_text:
        medicines.append("Amlodipine 5mg - Take 1 tablet daily for blood pressure control.")

    # Condition for cholesterol (e.g., Atorvastatin)
    if "cholesterol" in extracted_text or "atorvastatin" in extracted_text:
        medicines.append("Atorvastatin 10mg - Take 1 tablet daily to lower cholesterol levels.")

    # Condition for allergies (e.g., Cetirizine)
    if "allergy" in extracted_text or "cetirizine" in extracted_text:
        medicines.append("Cetirizine 10mg - Take 1 tablet once daily for allergy relief.")

    # Condition for acid reflux (e.g., Omeprazole)
    if "acid reflux" in extracted_text or "omeprazole" in extracted_text:
        medicines.append("Omeprazole 20mg - Take 1 tablet daily before meals for acid reflux.")

    # Condition for anxiety (e.g., Alprazolam)
    if "anxiety" in extracted_text or "alprazolam" in extracted_text:
        medicines.append("Alprazolam 0.25mg - Take 1 tablet as needed for anxiety.")

    # Condition for Asthma (e.g., Salbutamol)
    if "asthma" in extracted_text or "salbutamol" in extracted_text:
        medicines.append("Salbutamol Inhaler - 2 puffs every 4-6 hours as needed.")

    # Condition for Gastrointestinal Issues (e.g., Pantoprazole)
    if "gastritis" in extracted_text or "pantoprazole" in extracted_text:
        medicines.append("Pantoprazole 40mg - Take 1 tablet daily before breakfast.")

    # Condition for Insomnia (e.g., Zolpidem)
    if "insomnia" in extracted_text or "zolpidem" in extracted_text:
        medicines.append("Zolpidem 10mg - Take 1 tablet before bedtime for sleep.")

    # Condition for Depression (e.g., Sertraline)
    if "depression" in extracted_text or "sertraline" in extracted_text:
        medicines.append("Sertraline 50mg - Take 1 tablet daily for mood stabilization.")

    # Condition for Viral Infections (e.g., Oseltamivir for flu)
    if "influenza" in extracted_text or "oseltamivir" in extracted_text or "flu" in extracted_text:
        medicines.append("Oseltamivir 75mg - Take 1 capsule twice daily for 5 days for flu.")

    # Condition for Skin Infections (e.g., Clotrimazole for fungal infections)
    if "fungal infection" in extracted_text or "clotrimazole" in extracted_text:
        medicines.append("Clotrimazole Cream - Apply twice daily to the affected area for fungal infections.")

    # Condition for Heart Disease (e.g., Aspirin)
    if "heart disease" in extracted_text or "aspirin" in extracted_text or "blood thinner" in extracted_text:
        medicines.append("Aspirin 81mg - Take 1 tablet daily as a blood thinner for heart disease.")

    # Condition for Migraine (e.g., Sumatriptan)
    if "migraine" in extracted_text or "sumatriptan" in extracted_text:
        medicines.append("Sumatriptan 50mg - Take 1 tablet at the onset of migraine symptoms.")

    # Condition for Diarrhea (e.g., Loperamide)
    if "diarrhea" in extracted_text or "loperamide" in extracted_text:
        medicines.append("Loperamide 2mg - Take 1 tablet after each loose stool, up to 4 tablets per day.")

    # Condition for Constipation (e.g., Lactulose)
    if "constipation" in extracted_text or "lactulose" in extracted_text:
        medicines.append("Lactulose 10ml - Take 10ml once or twice daily to relieve constipation.")

    if "Oral Rehydration Salts" in extracted_text or "ORS" in extracted_text:
        medicines.append("Dissolve 1 sachet of ORS in 1 liter of clean water. Drink small sips frequently throughout the day. Duration: As needed to prevent dehydration.")
    

    # Default message if no specific recommendation found
    if not medicines:
        medicines.append("No specific medicine recommendation found.")
    
    return medicines




