# OCR Project Interview Preparation Guide

## Project Overview

**Production-ready UAE Document OCR API** with:
- FastAPI
- Gemini Vision OCR
- JWT Authentication
- Rate limiting
- Multi-API-Key load balancing
- 12+ official document types supported
- PDF → image conversion
- JSON validation

---

## Q: How did you handle MRZ numbers on images of passports or other documents in your OCR project?

**A:** I used an advanced OCR pipeline that included orientation correction and specific logic for MRZ (Machine Readable Zone) extraction. My approach involved:

- Ensuring the image was properly oriented before text extraction.
- Using a prompt-driven vision model to extract all passport fields, with special attention to MRZ lines and passport numbers.
- Applying rules to distinguish between similar-looking characters (e.g., 'I' vs '1') based on passport number patterns.
- Returning all extracted data in a clean, structured JSON format, with dates strictly in YYYY-MM-DD and missing fields as null.
- Removing all special/non-printable characters for a clean output.

This ensured high accuracy and reliability in extracting MRZ and other key details from passport images.

---

## Complete MRZ Handling Flow

```
Passport Image (with MRZ)
         ↓
Orientation Correction (if needed)
         ↓
Gemini Vision AI reads entire passport
         ↓
Extracts MRZ lines + visual text
         ↓
Character Disambiguation (I vs 1, O vs 0)
         ↓
Pattern-based validation (passport format)
         ↓
Clean special characters
         ↓
Convert dates to YYYY-MM-DD
         ↓
Validate required fields
         ↓
Return structured JSON
```

### How MRZ Extraction Works in Your Project

#### 1. **Prompt-Based MRZ Extraction**

You use a **vision-based AI approach** with Google Gemini. The key prompt instruction:

```python
prompt = """
Pay special attention to the passport number and other alphanumeric codes (e.g., MRZ lines).
If a character could be a capital letter "I" or the digit "1", choose the correct one based on typical passport number patterns.
Do NOT convert capital letters to digits or digits to letters automatically.
"""
```

#### 2. **Character Disambiguation**

Your approach addresses common MRZ OCR problems:

| Similar Characters | How You Handle It                            |
| ------------------ | -------------------------------------------- |
| **I vs 1**         | AI decides based on passport number patterns |
| **O vs 0**         | Context-aware recognition                    |
| **S vs 5**         | Pattern-based selection                      |

**Example**: Indian passports start with a letter (like "J1234567"), so the AI knows "J" is a letter, not a digit.

#### 3. **Orientation Correction**

```python
prompt = """
If the provided image contains text that is not properly oriented, 
correct its orientation before extracting the text.
"""
```

#### 4. **Data Validation**

Required MRZ fields validated:
- Passport Number (`id`)
- Date of Birth (`dob`)
- Country Code (`code`)
- Issue Date (`issuedate`)
- Expiry Date (`expirydate`)
- Nationality

#### 5. **Clean Output**

```python
prompt = """
Remove all special characters such as newline (\n), tab (\t), 
or any other non-printable characters from the text.
"""
```

MRZ special characters (`<`, `<<`, etc.) are automatically cleaned.

#### 6. **Date Format Standardization**

MRZ dates converted from `YYMMDD` format to `YYYY-MM-DD`.

### Interview Answer for MRZ Handling

**Q: How do you handle MRZ extraction?**

**A:** "I use Google's Gemini Vision AI with a carefully crafted prompt that:

1. **Automatically corrects image orientation** before reading
2. **Pays special attention to MRZ lines** and alphanumeric codes
3. **Intelligently disambiguates similar characters** (I vs 1, O vs 0) based on passport number patterns - for example, knowing Indian passports start with a letter followed by digits
4. **Removes MRZ special characters** (like `<` and `<<`) for clean output
5. **Standardizes date formats** from MRZ format to YYYY-MM-DD
6. **Validates all critical MRZ fields** (passport number, DOB, country code, dates, nationality)

This vision-based approach is more robust than traditional OCR because it understands context and patterns, not just character shapes."

### Why This Approach Works Better

| Traditional OCR              | Your Vision AI Approach            |
| ---------------------------- | ---------------------------------- |
| Struggles with I vs 1        | Context-aware disambiguation       |
| Requires pre-processing      | Auto-corrects orientation          |
| Fixed character recognition  | Pattern-based validation           |
| Needs MRZ-specific libraries | Single AI model handles everything |
| Brittle to image quality     | Robust to variations               |

---

## Complete Request Flow: Client to Response

### Step-by-Step Request Processing

#### 1️⃣ Client Makes Request

```
Client (Browser/Postman/App)
    ↓
POST http://your-server:8000/extract_passport_details
Headers: Authorization: your-secret-token
Body: image file (passport.jpg)
```

#### 2️⃣ Nginx Receives Request (FIRST ENTRY POINT)

**Location**: `nginx.conf` - Port 8000

**What Nginx Does**:
- ✅ **Validates file size** (rejects if > 200MB)
- ✅ **Adds headers** (X-Real-IP, X-Forwarded-For)
- ✅ **Selects backend server** (using least_conn algorithm)
- ✅ **Forwards request** to FastAPI app

```nginx
location / {
    proxy_pass http://fastapi_app;  # → Routes to app:8000
    proxy_read_timeout 600s;  # Allows 10 min processing time
}
```

#### 3️⃣ FastAPI Receives Request

**Processing Order**:

**A. SlowAPI Middleware (Rate Limiting)**
- ✅ Checks: Has this IP made > 5 requests in last minute?
- ❌ If YES → Returns `429 Too Many Requests`
- ✅ If NO → Continues to next step

**B. Dependency Injection (Token Verification)**
- ✅ Checks: Is Authorization header present?
- ✅ Checks: Does token match SECRET_TOKEN from .env?
- ❌ If NO → Returns `401/403 Unauthorized`
- ✅ If YES → Continues to endpoint function

#### 4️⃣ Endpoint Function Executes

**A. File Validation**
```python
if not image:
    return JSONResponse(content={"error": "No file part"}, status_code=400)

if image.filename == '':
    return JSONResponse(content={"error": "No selected file"}, status_code=400)

file_ext = image.filename.lower().split('.')[-1]
```

**B. File Type Processing**
```python
if file_ext in ['jpg', 'jpeg', 'png']:
    image_data = await image.read()  # Read bytes from upload
    image = Image.open(BytesIO(image_data))  # Convert to PIL Image

elif file_ext == 'pdf':
    pdf_bytes = await image.read()
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = pdf_document.load_page(0)  # First page only
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2x resolution
    image = Image.open(BytesIO(pix.tobytes("png")))
```

#### 5️⃣ OCR Processing (Google Gemini AI)

```python
data, status_code = await pass_ocr_extraction(image)
```

**What happens in `api_functions.py`**:
1. Gets a Gemini AI model from the pre-loaded pool (lifespan)
2. Sends PIL Image to Google's Gemini API
3. AI extracts passport details (name, number, dates, etc.)
4. Returns structured JSON data

#### 6️⃣ Response Formatting

```python
if status_code == 200:
    result = {"data": data, "sts": 200, "msg": "Success"}
    return JSONResponse(content=result, status_code=200)

elif status_code == 400:
    result = {"msg": "Document not suitable", "sts": 400}
    return JSONResponse(content=result, status_code=400)
```

#### 7️⃣ Response Travels Back

```
FastAPI → Nginx → Client
```

---

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ CLIENT                                                       │
│ POST http://server:8000/extract_passport_details           │
│ Authorization: secret-token                                 │
│ Body: passport.jpg (5MB)                                    │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ① NGINX (Port 8000)                                         │
│ ✓ File size check (< 200MB)                                │
│ ✓ Add headers (X-Real-IP)                                  │
│ ✓ Load balance (least_conn)                                │
│ ✓ Set timeout (600s)                                       │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ② FASTAPI APP (Port 8000)                                   │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ SlowAPI Middleware                                   │   │
│ │ ✓ Rate limit check (5/min per IP)                  │   │
│ └───────────────────┬─────────────────────────────────┘   │
│                     ↓                                       │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Token Verification (Depends)                        │   │
│ │ ✓ Check Authorization header                        │   │
│ │ ✓ Validate token against SECRET_TOKEN              │   │
│ └───────────────────┬─────────────────────────────────┘   │
│                     ↓                                       │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Endpoint Function                                   │   │
│ │ ✓ Validate file exists                              │   │
│ │ ✓ Check file extension                              │   │
│ │ ✓ Read bytes from UploadFile                        │   │
│ │ ✓ Convert to PIL Image                              │   │
│ └───────────────────┬─────────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ③ GOOGLE GEMINI AI API                                      │
│ ✓ Process image with AI model                              │
│ ✓ Extract passport fields                                  │
│ ✓ Return structured JSON                                   │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ④ RESPONSE                                                  │
│ {                                                           │
│   "data": {                                                 │
│     "passport_number": "AB1234567",                        │
│     "name": "John Doe",                                    │
│     "expiry_date": "2030-12-31"                            │
│   },                                                        │
│   "sts": 200,                                              │
│   "msg": "Success"                                         │
│ }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     ↓
                  CLIENT
```

---

## File Upload Processing Flow

```
Client Upload (JPG/PNG/PDF)
         ↓
    Validation
         ↓
   File Type Check
         ↓
    ┌────┴────┐
    ↓         ↓
  Image      PDF
    ↓         ↓
Read Bytes  Read Bytes → Convert to Image (PyMuPDF)
    ↓         ↓
    └────┬────┘
         ↓
   PIL Image Object
         ↓
Google Gemini AI (OCR)
         ↓
  Extracted Data (JSON)
         ↓
   Return to Client
```

---

## PDF to Image Conversion Process

```
PDF file
 ↓
Read as bytes
 ↓
Open PDF using PyMuPDF
 ↓
Load page
 ↓
Render page as image (high DPI)
 ↓
Convert to PNG bytes
 ↓
Convert to PIL Image
 ↓
OCR processing
```

### Why Matrix(2.0, 2.0) Is Important 🔥

**Say this if asked:**

*"Scaling the PDF page increases resolution, which improves text clarity and OCR accuracy, especially for small fonts."*

---

## Nginx Architecture

### Purpose of Nginx

#### 1. Reverse Proxy (Entry Point)

```
Client Request → Nginx (Port 8000) → FastAPI App (Port 8000)
```

- **Single entry point**: All client requests go through Nginx first
- **Hides backend**: Clients don't directly access your FastAPI servers
- **Security layer**: Nginx sits between the internet and your application

#### 2. Load Balancing

```nginx
upstream fastapi_app {
    least_conn;  # Route to server with least connections
    server app:8000;
}
```

#### 3. Large File Upload Handling

```nginx
client_max_body_size 200M;
```

Allows uploads up to 200MB (important for high-res images/PDFs)

#### 4. Extended Timeouts for OCR Processing

```nginx
proxy_connect_timeout 600s;  # 10 minutes
proxy_send_timeout 600s;
proxy_read_timeout 600s;
```

### Architecture Diagram

```
Internet
    ↓
Nginx (Port 8000)
    ↓ (Load Balancer)
    ├─→ FastAPI App Instance 1 (app:8000)
    ├─→ FastAPI App Instance 2 (app:8000)  ← Can scale with docker-compose
    └─→ FastAPI App Instance 3 (app:8000)
```

---

## Middleware Stack

### Middleware Execution Order

```
1. Nginx (receives request)
   ↓
2. FastAPI receives proxied request
   ↓
3. SlowAPIMiddleware (checks rate limit)
   ↓
4. FastAPI built-in middleware (exception handling)
   ↓
5. Your endpoint function
   ↓
6. Response flows back through middleware stack
   ↓
7. Nginx sends response to client
```

### Middleware Components

| Middleware            | Type           | Purpose                  | Status   |
| --------------------- | -------------- | ------------------------ | -------- |
| **SlowAPIMiddleware** | Application    | Rate limiting            | ✅ Active |
| **Nginx Proxy**       | Infrastructure | Load balancing, timeouts | ✅ Active |
| **FastAPI Defaults**  | Application    | Error handling           | ✅ Active |

---

## Libraries Used and Their Purpose

### Core Libraries

| Library                      | Purpose                                                 |
| ---------------------------- | ------------------------------------------------------- |
| **FastAPI**                  | For creating APIs and handling requests                 |
| **slowapi**                  | For rate limiting (5 requests per minute)               |
| **python-jose**              | For JWT token creation & verification                   |
| **passlib (bcrypt)**         | For password hashing & verification                     |
| **google.generativeai**      | For calling Gemini Vision API (OCR engine)              |
| **Pillow (PIL)**             | For opening and working with images (JPG/PNG)           |
| **PyMuPDF (fitz)**           | For reading PDF files and converting PDF pages → images |
| **python-dotenv**            | For loading `.env` file (API keys)                      |
| **re (Regular Expressions)** | For cleaning text and extracting patterns               |
| **json**                     | For parsing and generating JSON data                    |
| **uvicorn**                  | FastAPI server runner (local / production)              |
| **BytesIO**                  | To convert raw bytes → image objects                    |
| **random**                   | To randomly select a Gemini model from the pool         |

---

## Detailed Library Explanations

### 1. FastAPI
Used for:
- Web server
- Request handling
- File upload
- Dependency injection (`verify_token`)
- Exception management

### 2. slowapi
Used for:
- **Rate limiting** (restricting to 5 requests/minute)
- Avoiding API abuse
- Handling IP-based throttling

### 3. python-jose
Used for:
- Creating JWT access tokens
- Creating refresh tokens
- Verifying tokens
- Encoding/decoding payloads

### 4. passlib (bcrypt)
Used for:
- Password hashing
- Password verification
- (Not used in OCR, only for login/auth)

### 5. google.generativeai (Gemini API)
Used for:
- Calling **Gemini Vision** OCR model
- Handling image + text prompts
- Generating structured JSON output
- **This is your main OCR engine**

### 6. Pillow (PIL)
Used for:
- Opening JPG/PNG files
- Loading images from bytes
- Converting PDF pages into PIL images

### 7. PyMuPDF (fitz)
Used for:
- Opening PDF files
- Extracting pages
- Converting PDF pages → images
- Increasing image resolution

### 8. python-dotenv
Used for:
- Loading `.env` file
- Loading multiple Google API keys
- Secure configuration

### 9. random
Used for:
- Randomly selecting which Gemini model to use
- To distribute load across multiple API keys

### 10. re (Regular Expressions)
Used for:
- Cleaning text fields
- Removing special characters
- Policy number extraction

### 11. json
Used for:
- Parsing JSON from Gemini output
- Returning JSON responses

### 12. uvicorn
Used to run the FastAPI server.

### 13. BytesIO
Used for:
- Converting byte streams → images
- Temporary in-memory handling of files

---

## What Happens After File Upload (Step-by-Step)

### STEP 1 — FastAPI Receives the Uploaded File

Example endpoint:
```python
@app1.post("/extract_passport_details")
async def extract_pass_details(image: UploadFile = File(...), ... )
```

FastAPI gives you an `UploadFile` object containing:
- filename
- content-type
- raw file bytes

If no file → return **400 Bad Request**.

### STEP 2 — File Type is Checked

The extension is extracted:
```python
file_ext = image.filename.lower().split('.')[-1]
```

You support four file formats:

| Extension  | Meaning  | Supported              |
| ---------- | -------- | ---------------------- |
| `jpg`      | image    | ✔                      |
| `jpeg`     | image    | ✔                      |
| `png`      | image    | ✔                      |
| `pdf`      | document | ✔                      |
| `doc/docx` | MS Word  | ❌ (commented-out code) |

If the extension is not allowed → return **400 invalid format**.

### STEP 3 — File Converted Into an Image

#### ✔ If the file is JPG/JPEG/PNG:

```python
image_data = await image.read()
image = Image.open(BytesIO(image_data))
```

So you load it as a **PIL Image** object.

#### ✔ If the file is a PDF:

You extract **the first page of the PDF** and convert it into an image:

```python
pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
page = pdf_document.load_page(0)
pix = page.get_pixmap(matrix=fitz.Matrix(2.0,2.0))
img_data = pix.tobytes("png")
image = Image.open(BytesIO(img_data))
```

This gives you a **high-resolution PNG image**.

### STEP 4 — The Image Is Sent to Gemini Vision API

Every endpoint calls one OCR function, for example:

```python
data, status_code = await pass_ocr_extraction(image)
```

Inside it:

#### 1. A Gemini model is selected from your model pool

```python
model = initialize_gemini_model()
```

This chooses a **random Google API key** for load balancing.

#### 2. A detailed prompt is built

Each document type has a different prompt telling Gemini:
- How to read the text
- What fields to extract
- Format must be **JSON**
- Dates converted to `YYYY-MM-DD`
- If unclear, return `null`

#### 3. The API call is made

```python
response = model.generate_content([prompt, image])
```

#### 4. Gemini returns JSON inside backticks

You strip the backticks and parse:

```python
parsed_data = json.loads(raw_content)
```

#### 5. You validate required fields

- If required fields are present → success (200)
- If missing or incorrect → fail (400)

### STEP 5 — Data Is Returned to FastAPI

Success example:
```json
{
  "data": { ...extracted fields... },
  "sts": 200,
  "msg": "Success"
}
```

Fail example:
```json
{
  "msg": "The provided document is not suitable...",
  "sts": 400
}
```

### STEP 6 — Token Verification (Before Extraction)

Every endpoint is protected:

```python
_: None = Depends(verify_token)
```

FastAPI extracts token → sends to:

```python
verify_token(token)
```

If token invalid → **401 Unauthorized**

If valid → extraction proceeds.

### STEP 7 — Rate Limiter Checks

Every route is limited:

```python
@limiter.limit("5/minute")
```

If too many requests → **429 Too Many Requests**

---

## Key Technical Concepts

### Why Read Bytes and Convert to PIL Image?

When a client uploads an image:

#### What `UploadFile` Actually Is
- `UploadFile` is **NOT** a PIL Image object
- It's a **file-like object** that represents the uploaded data
- It's essentially a **stream of bytes** coming over HTTP
- Think of it as a "pipe" carrying data, not the actual image

#### Why Read Bytes?
```python
image_data = await image.read()  # Returns: bytes
```

- The uploaded file exists in **memory as a stream**
- We need to **read the entire stream** to get the actual image data
- `await image.read()` extracts all the bytes from the upload stream
- This gives us the **raw binary data** of the image file

#### Why Convert to PIL Image?
```python
image = Image.open(BytesIO(image_data))  # PIL Image object
```

**We need PIL Image because:**

1. **Google Gemini API requires PIL Image format**
2. **PIL Image provides image manipulation capabilities**
   - Resize, crop, rotate
   - Format conversion
   - Color space adjustments
   - Metadata extraction
3. **BytesIO creates an in-memory file**
   - `BytesIO(image_data)` wraps bytes in a file-like interface
   - `Image.open()` can read from this in-memory file
   - **No disk I/O needed** - everything stays in RAM

### Real-World Analogy

Think of it like receiving a package:

1. **UploadFile** = The delivery truck (carries the package)
2. **await image.read()** = Unloading the package from the truck
3. **image_data (bytes)** = The sealed box (raw data)
4. **BytesIO** = Opening the box
5. **PIL Image** = The actual product inside (usable image)

---

## Purpose of `lifespan` in FastAPI

The `lifespan` parameter is a **context manager** that controls what happens during the **startup and shutdown** of your FastAPI application.

### Implementation

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_model_pool()  # ✅ Load your model pool once
    yield
    # (Optional cleanup logic)
```

### How It Works

1. **Before `yield` (Startup)**:
   - Runs **once** when the application starts
   - In your case: `setup_model_pool()` initializes the Google Gemini AI model pool
   - This happens **before** the API starts accepting requests

2. **At `yield`**:
   - The application runs normally and handles requests
   - Your API endpoints are now active

3. **After `yield` (Shutdown)**:
   - Runs when the application is shutting down
   - Used for cleanup (closing connections, releasing resources)

### Benefits

1. **Performance**: 
   - Google Gemini AI models are loaded **once** at startup
   - Not reloaded on every request (which would be extremely slow)

2. **Resource Efficiency**:
   - Model stays in memory throughout the application lifecycle
   - Reduces memory allocation/deallocation overhead

3. **Faster Response Times**:
   - First request doesn't have the overhead of loading models
   - All requests use the pre-loaded model pool

### Real-World Impact

**Without lifespan:**
- Each OCR request: ~10-15 seconds (model loading + processing)

**With lifespan:**
- Each OCR request: ~2-5 seconds (just processing)
- Model loading happens once at startup: ~5-10 seconds

---

## Rate Limiting Purpose

Rate limiting in your project serves several critical purposes:

### 1. Protect Against API Abuse
- Prevents malicious users from overwhelming your service with excessive requests
- Stops automated bots from making thousands of requests in a short time
- Protects your infrastructure from being overloaded

### 2. Cost Control (Google AI API)
Since your application uses Google's Gemini AI API for OCR extraction, rate limiting helps:
- **Control API costs**: Each request to Google's AI services costs money
- **Prevent budget overruns**: Without rate limiting, a single user could rack up huge bills
- **Manage quota usage**: Google APIs have usage quotas and rate limits themselves

### 3. Resource Management
Your OCR operations are computationally expensive:
- **Image processing**: Converting PDFs to images, processing large files
- **AI model inference**: Running Gemini AI models takes time and resources
- **Memory usage**: Each request loads images into memory
- **Server capacity**: Limits concurrent processing to prevent server crashes

### 4. Fair Usage
- Ensures all users get equal access to the service
- Prevents one user from monopolizing resources
- Maintains consistent response times for everyone

### 5. Security Layer
- **DDoS protection**: Mitigates distributed denial-of-service attacks
- **Brute force prevention**: Slows down attempts to guess authentication tokens
- **Service availability**: Keeps the API responsive even under attack

### Current Configuration

```python
@limiter.limit("5/minute")  # 5 requests per minute per IP address
```

This means:
- Each IP address can make **5 requests per minute** to each endpoint
- After 5 requests, users get a `429 Too Many Requests` error
- The counter resets every minute

---

## Timeline Example

| Time   | Component      | Action                        |
| ------ | -------------- | ----------------------------- |
| 0ms    | Client         | Sends POST request            |
| 5ms    | **Nginx**      | Receives, validates, forwards |
| 10ms   | **SlowAPI**    | Checks rate limit ✅           |
| 15ms   | **Token Auth** | Validates token ✅             |
| 20ms   | **FastAPI**    | Reads file bytes              |
| 50ms   | **FastAPI**    | Converts to PIL Image         |
| 100ms  | **Gemini AI**  | Processes OCR (2-5 seconds)   |
| 5100ms | **FastAPI**    | Formats response              |
| 5105ms | **Nginx**      | Sends to client               |
| 5110ms | Client         | Receives JSON response        |

**Total**: ~5 seconds for OCR processing

---

## Final Summary

When a user uploads an image or PDF:

1. File arrives at FastAPI route
2. Extension is verified
3. PDF → image conversion if needed
4. Image is sent to Gemini Vision
5. Gemini returns JSON
6. Your code validates and cleans it
7. Response is returned
8. Token + rate-limit checks secure the route

Everything is powered by:

### **FastAPI + Gemini Vision OCR + JWT + SlowAPI rate limiter + PyMuPDF + Pillow**

---

## Key Interview Points

### Architecture Highlights
- Production-ready microservices architecture
- Nginx as reverse proxy and load balancer
- Horizontal scalability with Docker Compose
- Multi-layer security (token auth + rate limiting)

### Technical Decisions
- In-memory processing (no disk I/O)
- Model pool initialization at startup (lifespan)
- Multi-API-key load balancing
- High-resolution PDF conversion (2x scaling)

### Performance Optimizations
- Pre-loaded AI models
- Async/await for non-blocking I/O
- Connection pooling via Nginx
- Efficient byte stream handling

### Security Features
- JWT token authentication
- Rate limiting (5 req/min)
- Input validation
- Nginx as security layer

---

## Additional Notes

- All file processing happens in memory using `BytesIO`
- Only the first page of PDFs is processed
- PDFs are converted at 2x resolution for better OCR accuracy
- Uses async processing for non-blocking operations
- Files are processed and discarded, not stored
- Supports 12+ UAE official document types
- Clean JSON output with strict date formatting (YYYY-MM-DD)
- Missing fields returned as `null`
- Special characters removed for clean output
