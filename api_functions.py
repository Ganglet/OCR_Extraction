import base64
import json
import os
import re
import requests
from io import BytesIO
import google.generativeai as genai
import random
from PIL import Image
from dotenv import load_dotenv
import os
import random
from dotenv import load_dotenv
import google.generativeai as genai


# Global model pool
gemini_model_pool = []

def setup_model_pool():
    global gemini_model_pool

    load_dotenv()
    keys_raw = os.environ.get("GOOGLE_API_KEYS")
    if not keys_raw:
        raise ValueError("GOOGLE_API_KEYS environment variable not set.")

    api_keys = [key.strip() for key in keys_raw.split(",") if key.strip()]
    if not api_keys:
        raise ValueError("No valid API keys found.")

    # Create one model per API key and store in pool
    for key in api_keys:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        gemini_model_pool.append(model)

def initialize_gemini_model():
    if not gemini_model_pool:
        raise RuntimeError("Model pool is not initialized.")
    return random.choice(gemini_model_pool)

def clean_alphanum(value):
    """Keep only alphanumeric characters and single spaces between words"""
    if value is None:
        return None
    # Remove all non-alphanumeric and non-space characters
    cleaned = re.sub(r'[^A-Za-z0-9 ]+', '', value)
    # Replace multiple spaces with a single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Strip leading/trailing spaces
    return cleaned.strip()

def clean_alpha(value):
    """Keep only alphanumeric characters and single spaces between words"""
    if value is None:
        return None
    """Keep only alphabetic characters and single spaces between words"""
    # Remove everything except letters and spaces
    cleaned = re.sub(r'[^A-Za-z ]+', '', value)
    # Normalize multiple spaces to a single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Trim leading/trailing spaces
    return cleaned.strip()


def extract_policy_number(card_no):
    if card_no is None:
        return None
    # Match the pattern: OIG/ME-<policy_number>/E/<something>
    match = re.search(r"OIG/ME-(\d+)/E/", card_no)
    return match.group(1) if match else None


# Asynchronous OCR function using Google API
async def pass_ocr_extraction(image_input):
    model = initialize_gemini_model()
    image = image_input
    # Prepare the prompt for the Gemini Pro Vision model
    prompt = """Act as an OCR assistant.
                            If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.  
                            If  provided image is not country passport then write its not country passport image.
                            Extract the following details from the provided image and return them in JSON format:
                            {
                                "Passport No": "",
                                "Surname": "",
                                "Given Names": "",
                                "Nationality": "",
                                "Country code": "",
                                "Date of Birth": "YYYY-MM-DD",
                                "Sex": "M/F",
                                "Place of Birth": "",
                                "Date of Issue": "YYYY-MM-DD",
                                "Issuing Authority or Place of Issue": "",
                                "Date of Expiry": "YYYY-MM-DD",
                                "Address": ""
                            }
                            Ensure high accuracy in data extraction.
                            In provided image, Date of Issue, Date of Expiry and Date of Birth must be return strictly in YYYY-MM-DD format in respective detail.
                            If any field is missing or unclear, return it as null.
                            Remove all special characters such as newline (\n), tab (\t), or 
                            any other non-printable characters from the text. The final output should be a clean, single-line string without escape sequences.
                            Pay special attention to the passport number and other alphanumeric codes (e.g., MRZ lines).
                            If a character could be a capital letter “I” or the digit “1”, choose the correct one based on typical passport number patterns (e.g., Indian passports start with a capital letter followed by digits).
                            Do NOT convert capital letters to digits or digits to letters automatically.
                """


    # Make the Gemini Pro Vision API call
    response = model.generate_content([prompt, image])
    raw_content = response.text

    # Remove Markdown-style JSON formatting if present
    if raw_content.startswith("```json"):
        raw_content = raw_content.strip("```json").strip("```")
        # Parse the response as JSON
        parsed_data = json.loads(raw_content)
        # Convert to required format
        data = {
            "id": clean_alphanum(parsed_data.get("Passport No", "")),
            "givennames": clean_alpha(parsed_data.get("Given Names", "")),
            "surname": clean_alpha(parsed_data.get("Surname", "")),
            "dob": parsed_data.get("Date of Birth", ""),
            "code": parsed_data.get("Country code", ""),
            "issuedate": parsed_data.get("Date of Issue", ""),
            "expirydate": parsed_data.get("Date of Expiry", ""),
            "address": parsed_data.get("Address", ""),
            "sex": parsed_data.get("Sex", ""),
            "nationality": parsed_data.get("Nationality", ""),
            "placeofissue": parsed_data.get("Issuing Authority or Place of Issue", ""),
            "placeofbirth": parsed_data.get("Place of Birth", "")

        }

        if data.get("id") and data.get("dob") and data.get("code") and data.get("issuedate") and data.get("expirydate") and data.get("nationality"):
            if data.get("givennames") or data.get("surname"):
                print(data)
                return data, 200
            else:
                data = raw_content
                return data, 400
        else:
            data = raw_content
            return data, 400
    else:
        data = raw_content
        return data, 400

# Asynchronous OCR function using Google API
async def visa_ocr_extraction(image_input):
    model = initialize_gemini_model()
    image = image_input

    # Prepare the prompt for the Gemini Pro Vision model
    prompt = """
                Read the text from right to left where applicable.
                            If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.
                            Extract the following details from the image and return them in JSON format:
                            {
                                "UID Number": "",
                                "File or Entry Permit No": "",
                                "Place of Issue": "",
                                "Passport No": "",
                                "Name": "",
                                "Profession": "",
                                "Sponsor": "",
                                "Accompanied_by": "",
                                "Date of Birth": "YYYY-MM-DD",
                                "Issue_Date": "YYYY-MM-DD",
                                "Expiry_Date": "YYYY-MM-DD"
                            }
                            Ensure high accuracy in data extraction.
                            In provided image, Issue_Date, Expiry_Date and Date of Birth must be return strictly in YYYY-MM-DD format in respective detail.
                            If any parameter is missing or unclear, return it as null.
                
                """

    # Make the Gemini Pro Vision API call
    response = model.generate_content([prompt, image])
    raw_content = response.text

    # Remove Markdown-style JSON formatting if present
    if raw_content.startswith("```json"):

        raw_content = raw_content.strip("```json").strip("```")
        # Parse the response as JSON
        parsed_data = json.loads(raw_content)

        data = {
                "id": parsed_data.get("File or Entry Permit No", ""),
                "name": clean_alpha(parsed_data.get("Name", "")),
                "uid": parsed_data.get("UID Number", ""),
                "dob": parsed_data.get("Date of Birth", ""),
                "issuedate": parsed_data.get("Issue_Date", ""),
                "expirydate": parsed_data.get("Expiry_Date", ""),
                "profession": clean_alphanum(parsed_data.get("Profession", "")),
                "sponsor": clean_alphanum(parsed_data.get("Sponsor", "")),
                "passport_id": clean_alphanum(parsed_data.get("Passport No", "")),
                "placeofissue": parsed_data.get("Place of Issue", ""),
        }

        if data.get("id") and data.get("name") and data.get("uid") and data.get("issuedate") and data.get("expirydate") and data.get("passport_id") and data.get("sponsor"):
            if data.get("dob") is None or data.get("dob") == "null":

                print(data)
                return data, 200
            else:
                data = raw_content
                return data, 400
        else:
            data = raw_content
            return data, 400

    else:
        data = raw_content
        return data, 400

# Asynchronous OCR function using Google API
async def eid_ocr_extraction(image_input):
    model = initialize_gemini_model()
    image = image_input

    # Prepare the prompt for the Gemini Pro Vision model
    prompt = """
                 If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.  
                Extract the following details from the image and return them in JSON format:
                    {
                        "ID_Number": "",
                        "Name": "",
                        "Date_of_Birth": "YYYY-MM-DD",
                        "Nationality": "",
                        "Issuing_Date": "YYYY-MM-DD",
                        "Expiry_Date": "YYYY-MM-DD",
                        "Occupation": "",
                        "Employer": "",
                        "Issuing_Place": ""
                    }
                    Ensure high accuracy in data extraction.
                    In provided image, Issuing_Date and Expiry_Date are in DD-MM-YYYY but return it in YYYY-MM-DD format in respective detail.
                    Ensure the extracted text is accurate. If a field is missing or unclear, return null.
                    """

    # Make the Gemini Pro Vision API call
    response = model.generate_content([prompt, image])
    raw_content = response.text

    # Remove Markdown-style JSON formatting if present
    if raw_content.startswith("```json"):

        raw_content = raw_content.strip("```json").strip("```")
        # Parse the response as JSON
        parsed_data = json.loads(raw_content)


        data = {
                "id": parsed_data.get("ID_Number", ""),
                "name": clean_alpha(parsed_data.get("Name", "")),
                "nationality": parsed_data.get("Nationality", ""),
                "dob": parsed_data.get("Date_of_Birth", ""),
                "issuedate": parsed_data.get("Issuing_Date", ""),
                "expirydate": parsed_data.get("Expiry_Date", ""),
                "occupation": parsed_data.get("Occupation", ""),
                "employer": parsed_data.get("Employer", ""),
                "placeofissue": parsed_data.get("Issuing_Place", "")

            }

        if data.get("id") and data.get("name") and data.get("nationality"):
            id_value = data.get("id", "")
            if "-" in id_value and id_value.replace("-", "").isdigit():
                print(data)
                return data, 200
            else:
                data = raw_content
                return data, 400
        else:
            data = raw_content
            return data, 400

    else:
        data = raw_content
        return data, 400

# Asynchronous OCR function using Google API
async def dl_ocr_extraction(image_input):
    model = initialize_gemini_model()
    image = image_input

    # Prepare the prompt for the Gemini Pro Vision model
    prompt = """
                If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.
                Extract the following details from the provided image and return them in structured JSON format:
                    {
                        "License No": "",
                        "Name": "",
                        "Nationality": "",
                        "Date_of_Birth": "YYYY-MM-DD",
                        "Issue_Date": "YYYY-MM-DD",
                        "Expiry_Date": "YYYY-MM-DD",
                        "Place_of_Issue": "",
                        "Traffic Code No":""
                    }
                    Ensure high accuracy in data extraction.
                    
                    If any parameter is missing or unclear, return null instead of guessing the value.
                    """


    # Make the Gemini Pro Vision API call
    response = model.generate_content([prompt, image])
    raw_content = response.text

    # Remove Markdown-style JSON formatting if present
    if raw_content.startswith("```json"):

        raw_content = raw_content.strip("```json").strip("```")
        # Parse the response as JSON
        parsed_data = json.loads(raw_content)

        data = {
                "id": parsed_data.get("License No", ""),
                "name": clean_alpha(parsed_data.get("Name", "")),
                "nationality": parsed_data.get("Nationality", ""),
                "dob": parsed_data.get("Date_of_Birth", ""),
                "issuedate": parsed_data.get("Issue_Date", ""),
                "expirydate": parsed_data.get("Expiry_Date", ""),
                "placeofissue": parsed_data.get("Place_of_Issue", ""),
                "traffic_code": parsed_data.get("Traffic Code No", "")

            }

        if data.get("id") and data.get("name") and data.get("dob") and data.get("issuedate") and data.get("expirydate") and data.get("placeofissue"):
            id_value = data.get("id", "")

            if id_value.isdigit() and len(id_value) <= 8:
                print(data)
                return data, 200
            else:
                data = raw_content
                return data, 400
        else:
            data = raw_content
            return data, 400

    else:
        data = raw_content
        return data, 400


async def e_visa_extraction(image_input):
    model = initialize_gemini_model()
    image=image_input
    prompt = """
                    If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.
                    Extract the following details from the provided image and return them in structured JSON format:
                        {
                            "Full Name":"",
                            "ENTRY PERMIT NO": "",
                            "Date of Issue": "YYYY-MM-DD",
                            "Place of Issue" :"",
                            "Nationality":"",
                            "Valid Until":"YYYY-MM-DD",
                            "U.I.D. No.":"",
                            "Date of Birth": "YYYY-MM-DD",
                            "Place of Birth":""
                            "Profession":"",
                            "Passport No":"",
                            "Employer":""
                        }
                        Ensure high accuracy in data extraction.
                        All extracted data must be in english. 
                        In provided image Date of Birth and Valid Until are in DD-MM-YYYY but return it in YYYY-MM-DD format in respective detail.
                        If any parameter is missing or unclear, return null instead of guessing the value.
                        """

    response = model.generate_content([prompt, image])
    raw_content = response.text
    # # Remove Markdown-style JSON formatting if present
    if raw_content.startswith("```json"):
        raw_content = raw_content.strip("```json").strip("```")

        parsed_data = json.loads(raw_content)
        data = {
            "id": parsed_data.get("ENTRY PERMIT NO", ""),
            "name":clean_alpha(parsed_data.get("Full Name","")),
            "nationality":parsed_data.get("Nationality",""),
            "uid": parsed_data.get("U.I.D. No.", ""),
            "expirydate": parsed_data.get("Valid Until", ""),
            "dob": parsed_data.get("Date of Birth", ""),
            "placeofbirth": parsed_data.get("Place of Birth", ""),
            "profession": parsed_data.get("Profession", ""),
            "passport_id": parsed_data.get("Passport No", ""),
            "issuedate": parsed_data.get("Date of Issue", ""),
            "placeofissue":parsed_data.get("Place of Issue",""),
            "sponsor": parsed_data.get("Employer", ""),

        }

        if (data.get("id") and data.get("name") and data.get("uid") and data.get("expirydate") and data.get("dob") and data.get("profession") and data.get("passport_id") and data.get("issuedate") and  data.get("sponsor")):
            print(data)
            if '/' in data.get("passport_id"):
                data["passport_id"] = data.get("passport_id").split('/')[-1].strip()

            return data, 200

        else:
            data = raw_content
            return data, 400


async def get_medical_fitness_data(image_input):
    model = initialize_gemini_model()
    image = image_input
    # Prepare the prompt for the Gemini Pro Vision model
    prompt = """
                  If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.  
                  Extract the following details from the image and return them in JSON format:
                      {
                          "Application ID":"",
                          "Visa Type":"",
                          "Urgency Category":"",
                          "Request Type":"",
                          "Medical Center":"",
                          "Paid Amount":"",
                          "Name": "",
                          
                      }
                      Ensure high accuracy in data extraction.
                      In the provided image, if any date is in DD-MM-YYYY format, return it as YYYY-MM-DD.
                      Ensure the extracted text is accurate. If a field is missing or unclear, return null.
              """

              # Make the Gemini Pro Vision API call
    response = model.generate_content([prompt, image])
    raw_content = response.text
    print(raw_content)
    # Remove Markdown-style JSON formatting if present
    if raw_content.startswith("```json"):
        raw_content = raw_content.strip("```json").strip("```")

        # Parse the response as JSON
        parsed_data = json.loads(raw_content)

        data = {
            "medical_ref_number": parsed_data.get("Application ID", ""),
            "name": clean_alpha(parsed_data.get("Name", "")),
            "visa_type": parsed_data.get("Visa Type", ""),
            "urgency_category": parsed_data.get("Urgency Category", ""),
            "request_type": parsed_data.get("Request Type", ""),
            "medical_center": parsed_data.get("Medical Center", ""),
            "paid_amount": parsed_data.get("Paid Amount", ""),

        }

        if data.get("medical_ref_number") and data.get("name") and data.get("request_type"):
            return data, 200

        else:
            data = raw_content
            return data, 400
    else:
        data = raw_content
        return data, 400


async def get_eid_application_details(image_input):
    model = initialize_gemini_model()
    image = image_input
    prompt = """
        If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.
        Extract the following details from the provided image and return them in structured JSON format:
        {
            "APPLICATION No": "",
            "AMOUNT PAID": "",
            "VALIDITY YEARS": "",
            "APPLICANT Type": "",
            "REQUEST Type": "",
            "PHONE No": "",
            "NAME": "",
            "NATIONALITY": "",
            "GENDER": "",
            "FILE NUMBER": "",
            "IDENTITY NUMBER": "",
            "UNIFIED NO": "",
            "SUBMITTED ON": "YYYY-MM-DD HH:MM:SS",
            "DATE OF BIRTH": "YYYY-MM-DD",
            "E-MAIL": "",
            "Appointment Location Detail":"",
            "Appointment date and time Detail":"YYYY-MM-DD HH:MM:SS",
            "Appointment reference number Detail":""
        }
        Ensure high accuracy in data extraction.
        All extracted data must be in English.
        In the provided image, dates are in DD-MM-YYYY format. Return them in YYYY-MM-DD format.
        While Extracting Appointment Details, extract proper location, datetime and reference number if present, Try to avoid unnecessary stop words.
        If any parameter is missing or unclear, return null instead of guessing the value.
        """

    response = model.generate_content([prompt, image])
    raw_content = response.text
    print(raw_content)
    # # Remove Markdown-style JSON formatting if present
    if raw_content.startswith("```json"):
        raw_content = raw_content.strip("```json").strip("```")

        parsed_data = json.loads(raw_content)

        data = {
            "application_no": parsed_data.get("APPLICATION No", ""),
            "amount_paid": parsed_data.get("AMOUNT PAID", ""),
            "validity_years": parsed_data.get("VALIDITY YEARS", ""),
            "applicant_type": parsed_data.get("APPLICANT Type", ""),
            "request_type": parsed_data.get("REQUEST Type", ""),
            "phone_no": parsed_data.get("PHONE No", ""),
            "name": clean_alpha(parsed_data.get("NAME", "")),
            "nationality": parsed_data.get("NATIONALITY", ""),
            "gender": parsed_data.get("GENDER", ""),
            "file_number": parsed_data.get("FILE NUMBER", ""),
            "identity_number": parsed_data.get("IDENTITY NUMBER", ""),
            "unified_no": parsed_data.get("UNIFIED NO", ""),
            "submitted_on": parsed_data.get("SUBMITTED ON", ""),
            "date_of_birth": parsed_data.get("DATE OF BIRTH", ""),
            "email": parsed_data.get("E-MAIL", ""),
            "appointment_loc": parsed_data.get("Appointment Location Detail", ""),
            "appointment_dt": parsed_data.get("Appointment date and time Detail", ""),
            "appointment_ref_no": parsed_data.get("Appointment reference number Detail", "")
        }

        if data.get("application_no") and data.get("amount_paid")and data.get("validity_years") and data.get("request_type") and data.get("name") and data.get("nationality") and data.get("file_number") and data.get("submitted_on") and data.get("date_of_birth"):
        # if data:

            if '\n' in data.get('application_no'):
                data['application_no']=data.get('application_no').split("\n")[0]

            return data, 200

        else:
            data = raw_content
            return data, 400

    else:
        data = raw_content
        return data, 400


async def mol_extraction(image_input):
    model = initialize_gemini_model()
    image = image_input
    prompt = """
        If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.
        Extract the following details from the provided image and return them in structured JSON format:
        {
            "Work Style":"",
            "Transaction Number": "",
            "Corresponding to": "YYYY-MM-DD",
            "Establishment Name": "",
            "Establishment No": "",
            "Represented by": "",
            "Passport No": "",
            "Nationality": "",
            "Title": "",
            "Emirate": "",
            "Telephone number": "",
            "E-MAIL": "",
            "Name": "",
            "Date of Birth": "YYYY-MM-DD",
            "Passport Number": "",
            "TelephoneNumber": "",
            "Academic Qualification": ""
        }
        Ensure high accuracy in data extraction.
        Extract all details in English only.
        In the provided image, dates are in DD-MM-YYYY format. Return them in YYYY-MM-DD format.
        If any parameter is missing or unclear, return null instead of guessing the value.
    """

    response = model.generate_content([prompt, image])
    raw_content = response.text
    print(raw_content)

    # Remove Markdown-style JSON formatting if present
    if raw_content.startswith("```json"):
        raw_content = raw_content.strip("```json").strip("```")

        parsed_data = json.loads(raw_content)

        data = {
            "mol_number": parsed_data.get("Transaction Number", ""),
            "work_style": parsed_data.get("Work Style"),
            "agreement_date": parsed_data.get("Corresponding to", ""),
            "establishment_name": parsed_data.get("Establishment Name", ""),
            "establishment_no": parsed_data.get("Establishment No", ""),
            "represented_by": parsed_data.get("Represented by", ""),
            "passport_no": parsed_data.get("Passport No", ""),
            "nationality": parsed_data.get("Nationality", ""),
            "title": parsed_data.get("Title", ""),
            "emirate": parsed_data.get("Emirate", ""),
            "first_party_contact_no": parsed_data.get("Telephone number", ""),
            "email": parsed_data.get("E-MAIL", ""),
            "name": clean_alpha(parsed_data.get("Name", "")),
            "date_of_birth": parsed_data.get("Date of Birth", ""),
            "passport_number": parsed_data.get("Passport Number", ""),
            "second_party_contact_no": parsed_data.get("TelephoneNumber", ""),
            "academic_qualification": parsed_data.get("Academic Qualification", "")
        }

        if data.get("mol_number") and data.get("agreement_date") and data.get("establishment_name") and data.get("establishment_no") and data.get("represented_by") and data.get("passport_no") and data.get("emirate") and data.get("name") and data.get("date_of_birth") and data.get("passport_number"):
            return data, 200

        else:
            data = raw_content
            return data, 400

    else:
        data = raw_content
        return data, 400


async def get_status_change_data(image_input):
    model = initialize_gemini_model()
    image = image_input
    # Prepare the prompt for the Gemini Pro Vision model
    prompt = """
                  If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.  
                  Extract the following details from the image and return them in JSON format:
                      {
                          "New File Number": "",
                          "Previous File No": "",
                          "U.I.D No.": "",
                          "Submission Date": "YYYY-MM-DD",
                          "Approval Date": "YYYY-MM-DD",
                          "Name": "",
                          "Nationality": "",
                          "Passport No": "",
                          "Profession": "",
                          "Sponsor Name": "",
                          "The residence must be stamped up to": "YYYY-MM-DD"
                      }
                      Ensure high accuracy in data extraction.
                      All extracted data must be in English.
                      In the provided image, dates like Submission Date, Approval Date, and 'The residence must be stamped up to' are in DD-MM-YYYY format but return them in YYYY-MM-DD format in respective fields.
                      Ensure the extracted text is accurate. If a field is missing or unclear, return null.
              """

    # Make the Gemini Pro Vision API call
    response = model.generate_content([prompt, image])
    raw_content = response.text
    print(raw_content)
    # Remove Markdown-style JSON formatting if present
    if raw_content.startswith("```json"):
        raw_content = raw_content.strip("```json").strip("```")
        # Parse the response as JSON
        parsed_data = json.loads(raw_content)
        # Convert to required format
        data = {
            "file_number": parsed_data.get("New File Number", ""),
            "previous_file_no": parsed_data.get("Previous File No", ""),
            "uid_no": parsed_data.get("U.I.D No.", ""),
            "submission_date": parsed_data.get("Submission Date", ""),
            "approval_date": parsed_data.get("Approval Date", ""),
            "name": parsed_data.get("Name", ""),
            "nationality": parsed_data.get("Nationality", ""),
            "passport_no": parsed_data.get("Passport No", ""),
            "profession": parsed_data.get("Profession", ""),
            "sponsor": parsed_data.get("Sponsor Name", ""),
            "residence_stamp_valid_date": parsed_data.get("The residence must be stamped up to", "")
        }

        if data.get("file_number") and data.get("previous_file_no") and data.get("uid_no") and data.get("submission_date") and data.get("approval_date") and data.get("name") and data.get("passport_no") and data.get("profession") and data.get("sponsor"):
            return data, 200
        else:
            data = raw_content
            return data, 400
    else:
        data = raw_content
        return data, 400


async def get_insurance_card_details(image_input):
    model = initialize_gemini_model()
    image = image_input

    prompt = """
                  If the provided image contains text that is not properly oriented, correct its orientation before extracting the text.  
                  Extract the following details from the image and return them in JSON format:
                      {
                          "Name": "",
                          "Gender": "",
                          "Marital Status": "",
                          "Birth": "YYYY-MM-DD",
                          "Valid From": "YYYY-MM-DD",
                          "Valid till": "YYYY-MM-DD",
                          "Category": "",
                          "Card No": "",
                          "Policy No":"",
                          "EID No": "",
                          "DHA ID": "",
                          "DoH ID" : ""
                      }
                  Ensure high accuracy and avoid hallucinating values.
                  All extracted data must be in English.
                  If document is from 'NATIONAL GENERAL INSURANCE CO. (PJSC)', ensure Policy/Card No starts with letter "I" (not digit "1"), e.g. "I038-000-119267051-01".
                  If "DHA ID" or "DoH ID" is not present in document return it as null.
                  In the provided image, dates like 'Birth', 'Valid From', 'Valid till' are in DD-MM-YYYY format but return them in YYYY-MM-DD format in respective fields.
                  Ensure the extracted text is accurate. If a field is missing or unclear, return null.
          """
    response = model.generate_content([prompt, image])
    raw_content = response.text
    print(raw_content)

    if raw_content.startswith("```json"):
        raw_content = raw_content.strip("```json").strip("```")
        # Parse the response as JSON
        parsed_data = json.loads(raw_content)
        # Convert to required format
        data = {
            "name": parsed_data.get("Name", ""),
            "gender": parsed_data.get("Gender", ""),
            "marital_status": parsed_data.get("Marital Status", ""),
            "dob": parsed_data.get("Birth", ""),
            "issue": parsed_data.get("Valid From", ""),
            "expiry": parsed_data.get("Valid till", ""),
            "category": parsed_data.get("Category", ""),
            "card_no": parsed_data.get("Card No", ""),
            "policy_number": parsed_data.get("Policy No", ""),
            "emiratesid_number": parsed_data.get("EID No", ""),
            "dha_id": parsed_data.get("DHA ID", ""),
            "doh_id": parsed_data.get("DoH ID", "")
        }

        print(f"final_data = {data}")
        if data.get("name") and data.get("marital_status") and data.get("issue") and data.get("expiry") and data.get("category") and data.get("card_no") and data.get("emiratesid_number"):
            # Add policy number to dictionary
            data["policy_number"] = extract_policy_number(data.get("card_no"))
            return data, 200
        elif data.get("name") and data.get("issue") and data.get("expiry") and data.get("category") and  data.get("policy_number"):
            return data, 200

        elif data.get("name") and data.get("issue") and data.get("expiry") and data.get("category") and data.get("card_no") and data.get("dob"):
            # Add policy number to dictionary
            data["policy_number"] = (data.get("card_no"))
            return data, 200
        else:
            data = raw_content
            return data, 400
    else:
        data = raw_content
        return data, 400

# Testing the functions in passport_ocr.py
if __name__ == "__main__":
    # Example test case
    pass
