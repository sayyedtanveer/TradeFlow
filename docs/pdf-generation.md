# PDF Generation Architecture

## Overview

MedTrack ERP uses **WeasyPrint** for enterprise document generation. This document explains the architecture, setup, and operational details for PDF generation across different environments.

---

## Why WeasyPrint?

WeasyPrint was chosen as the official PDF engine for several reasons:

1. **HTML/CSS-based**: Leverages existing web design skills - templates use standard HTML/CSS
2. **Python-native**: No external processes or system calls required
3. **Production-ready**: Battle-tested in enterprise environments
4. **Typography support**: Advanced text rendering, fonts, and Unicode support
5. **CSS Paged Media**: Supports print-specific CSS features (page breaks, headers/footers)
6. **Template-friendly**: Works seamlessly with Jinja2 for dynamic content

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Work Orders  │  │ PO Detail   │  │ Invoice Det  │      │
│  │ Detail Page  │  │ Page        │  │ Page        │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            ▼                                 │
│                 documentService.ts                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  documents.py (API Routes)                           │  │
│  │  - POST /{document_type}/{entity_id}/generate        │  │
│  │  - GET /{document_id}/download                       │  │
│  │  - GET /{document_id}/preview                        │  │
│  │  - GET /test/pdf                                     │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  DocumentGenerationService (Orchestrator)            │  │
│  │  - Coordinates template, PDF, storage, repository   │  │
│  │  - Handles versioning logic                         │  │
│  └──────────┬──────────────┬──────────────┬───────────┘  │
│             ▼              ▼              ▼               │
│  ┌────────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ TemplateService│ │PDFGeneration │ │StorageService│   │
│  │ (Jinja2)       │ │ (WeasyPrint) │ │ (Filesystem) │   │
│  └────────────────┘ └──────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Frontend Request**: User clicks "Print" or "Download PDF" button
2. **API Call**: `POST /api/v1/documents/{document_type}/{entity_id}/generate`
3. **Context Builder**: Fetches entity data (PO, Invoice, Work Order, etc.)
4. **Template Rendering**: Jinja2 renders HTML template with context
5. **PDF Generation**: WeasyPrint converts HTML to PDF bytes
6. **Storage**: PDF saved to `/app/storage/documents/{tenant_id}/{document_type}/`
7. **Database Record**: Document metadata stored in `documents` table
8. **Response**: Returns document ID and file path to frontend
9. **Download/Preview**: Frontend calls download/preview endpoint

---

## Docker Setup

### Dockerfile Configuration

The Dockerfile includes all required WeasyPrint system dependencies:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu \
    libharfbuzz0b \
    libfribidi0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*
```

### Docker Compose

```yaml
backend:
  volumes:
    - documents_data:/app/storage/documents

volumes:
  documents_data:
```

This ensures PDFs persist between container restarts.

---

## Linux Dependencies

WeasyPrint requires the following GTK/Cairo libraries:

| Package | Purpose |
|---------|---------|
| libcairo2 | 2D graphics library |
| libpango-1.0-0 | Text layout and rendering |
| libpangocairo-1.0-0 | Pango/Cairo integration |
| libgdk-pixbuf-2.0-0 | Image loading |
| libffi-dev | Foreign Function Interface |
| shared-mime-info | MIME type detection |
| fonts-dejavu | Default fonts |
| libharfbuzz0b | Text shaping |
| libfribidi0 | Bidirectional text |
| libjpeg-dev | JPEG support |
| libopenjp2-7-dev | JPEG 2000 support |

### Installation by Distribution

**Ubuntu/Debian:**
```bash
sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info fonts-dejavu libharfbuzz0b libfribidi0 libjpeg-dev libopenjp2-7-dev
```

**Fedora/RHEL:**
```bash
sudo dnf install cairo pango gdk-pixbuf2 libffi shared-mime-info dejavu-fonts harfbuzz fribidi libjpeg-turbo openjpeg2
```

**macOS:**
```bash
brew install cairo pango gdk-pixbuf libffi
```

---

## Windows Local Development

### Issue

WeasyPrint requires GTK libraries which are not available on Windows by default. Attempting to import WeasyPrint on Windows without GTK will result in:

```
OSError: cannot load library 'gobject-2.0-0'
```

### Solution Options

**Option 1: Use Docker (Recommended)**
```bash
docker-compose up --build
```
All dependencies are pre-installed in the Docker image.

**Option 2: Install GTK on Windows**
1. Install MSYS2 from https://www.msys2.org/
2. Run MSYS2 and install GTK packages:
```bash
pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-cairo mingw-w64-x86_64-pango
```
3. Add MSYS2 bin directory to PATH

**Option 3: Graceful Fallback**
The backend includes graceful fallback logic. If WeasyPrint is unavailable:
- Backend starts successfully
- PDF generation disabled
- Warning logged: "WeasyPrint dependencies missing"
- Other functionality unaffected

### Graceful Fallback Implementation

```python
# pdf_generation_service.py
WEASYPRINT_AVAILABLE = False
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint imported successfully - PDF generation enabled")
except (ImportError, OSError) as e:
    logger.warning(f"WeasyPrint not available: {e} - PDF generation disabled")

class PDFGenerationService:
    def __init__(self, base_url: Optional[str] = None):
        self.available = WEASYPRINT_AVAILABLE
    
    def generate_pdf_from_html(self, html_content: str, css_content: Optional[str] = None) -> bytes:
        if not self.available:
            raise RuntimeError("PDF generation is not available. WeasyPrint dependencies are missing.")
        # ... PDF generation logic
```

---

## Document Storage Structure

### Filesystem Layout

```
/app/storage/documents/
├── {tenant_id}/
│   ├── work_orders/
│   │   ├── {entity_id}_v1_20240101_120000.pdf
│   │   └── {entity_id}_v2_20240102_140000.pdf
│   ├── purchase_orders/
│   │   └── {entity_id}_v1_20240101_130000.pdf
│   ├── invoices/
│   │   └── {entity_id}_v1_20240101_140000.pdf
│   ├── delivery_challans/
│   │   └── {entity_id}_v1_20240101_150000.pdf
│   └── qc_reports/
│       └── {entity_id}_v1_20240101_160000.pdf
```

### File Naming Convention

`{entity_id}_v{version_number}_{timestamp}.pdf`

Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890_v1_20240101_120000.pdf`

### Storage Service

The `DocumentStorageService` handles:
- Automatic directory creation (`mkdir -p`)
- Unique file path generation
- File read/write operations
- File deletion

```python
storage_service = DocumentStorageService(base_storage_path="storage/documents")
file_path = storage_service.generate_file_path(
    tenant_id=tenant_id,
    document_type="work_order",
    entity_id=entity_id,
    version_number=1,
)
storage_service.save_pdf(pdf_bytes, file_path)
```

---

## Document Types

### Supported Document Types

| Type | Template Path | Context Builder | Use Case |
|------|---------------|-----------------|----------|
| work_order | `templates/work_order/print.html` | `_build_work_order_context` | Manufacturing work orders |
| purchase_order | `templates/purchase_order/print.html` | `_build_purchase_order_context` | Supplier purchase orders |
| invoice | `templates/invoice/print.html` | `_build_invoice_context` | Customer invoices |
| delivery_challan | `templates/delivery_challan/print.html` | `_build_delivery_challan_context` | Delivery notes |
| qc_report | `templates/qc_report/print.html` | `_build_qc_report_context` | Quality inspection reports |

### Template Structure

All templates extend a base template for consistent styling:

```html
{% extends "base.html" %}

{% block content %}
<div class="header">
  <!-- Tenant branding -->
</div>
<div class="document-title">{{ title }}</div>
<div class="document-meta">
  <!-- Document metadata -->
</div>
<table>
  <!-- Document items -->
</table>
<div class="signatures">
  <!-- Signatures -->
</div>
{% endblock %}
```

---

## API Endpoints

### Generate Document

```http
POST /api/v1/documents/{document_type}/{entity_id}/generate
```

**Request Body:**
```json
{
  "force_regenerate": false
}
```

**Response:**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "document_type": "work_order",
  "entity_id": "uuid",
  "version_number": 1,
  "file_path": "/app/storage/documents/...",
  "generated_at": "2024-01-01T12:00:00Z"
}
```

### Download Document

```http
GET /api/v1/documents/{document_id}/download
```

Returns PDF file as `application/pdf` with `Content-Disposition` header.

### Preview Document

```http
GET /api/v1/documents/{document_id}/preview
```

Returns PDF file for inline viewing.

### List Document Versions

```http
GET /api/v1/documents/{document_type}/{entity_id}/versions
```

Returns all versions for a specific entity.

### Test PDF Generation

```http
GET /api/v1/documents/test/pdf
```

Generates a simple test PDF to validate WeasyPrint setup.

**Response:**
```json
{
  "success": true,
  "message": "PDF generated successfully",
  "file_path": "/app/storage/documents/...",
  "file_size": 12345
}
```

---

## Troubleshooting

### WeasyPrint Import Error

**Symptom:**
```
OSError: cannot load library 'gobject-2.0-0'
```

**Solution:**
- Docker: Ensure Dockerfile includes WeasyPrint dependencies
- Linux: Install GTK packages (see Linux Dependencies section)
- Windows: Use Docker or install GTK via MSYS2

### PDF Generation Disabled

**Symptom:**
```
RuntimeError: PDF generation is not available. WeasyPrint dependencies are missing.
```

**Solution:**
- Check logs for WeasyPrint import warnings
- Verify system dependencies are installed
- Use Docker for consistent environment

### Template Not Found

**Symptom:**
```
TemplateNotFound: template not found
```

**Solution:**
- Verify template exists in `backend/app/templates/{document_type}/print.html`
- Check TemplateService base path configuration

### Storage Permission Error

**Symptom:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
- Ensure `/app/storage/documents` directory exists
- Check write permissions
- Verify Docker volume mount is correct

### PDF Blank or Corrupted

**Symptom:**
- PDF generates but appears blank
- PDF file size is suspiciously small

**Solution:**
- Check template syntax (valid HTML)
- Verify context data is being passed correctly
- Test with simple inline template
- Check WeasyPrint logs for rendering errors

---

## Render.com Deployment

### Compatibility

The Dockerfile is fully compatible with Render.com:
- Uses `python:3.11-slim` base image (Linux)
- All WeasyPrint dependencies installed via apt
- No Windows-specific assumptions
- No manual GTK setup required

### Deployment Steps

1. **Push Code to Git Repository**
   ```bash
   git add .
   git commit -m "Add PDF generation support"
   git push
   ```

2. **Connect Repository to Render**
   - Go to Render Dashboard
   - Click "New Web Service"
   - Connect your Git repository

3. **Configure Build**
   - Build Command: `docker build -t medtrack .`
   - Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

4. **Environment Variables**
   - Copy from `.env.example`
   - Set `DATABASE_URL` to Render PostgreSQL
   - Set `REDIS_URL` to Render Redis (optional)

5. **Deploy**
   - Render builds Docker image automatically
   - WeasyPrint dependencies installed during build
   - PDF generation works out-of-the-box

### Render-Specific Considerations

- **Storage**: Render provides ephemeral filesystem. For persistent PDF storage, consider:
  - Render Disk (persistent storage add-on)
  - S3-compatible object storage (future migration)
  
- **Environment**: Render uses Linux, so WeasyPrint works natively

---

## Future S3/Cloud Migration

### Current Architecture

The storage layer is abstracted through `DocumentStorageService`:

```python
class DocumentStorageService:
    def save_pdf(self, pdf_bytes: bytes, file_path: str) -> None:
        path = Path(file_path)
        path.write_bytes(pdf_bytes)
```

### Migration Path

To migrate to S3 or cloud storage:

1. **Create Cloud Storage Service**
```python
class CloudStorageService:
    def __init__(self, s3_client, bucket_name: str):
        self.s3_client = s3_client
        self.bucket_name = bucket_name
    
    def save_pdf(self, pdf_bytes: bytes, key: str) -> str:
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=pdf_bytes,
            ContentType='application/pdf'
        )
        return f"s3://{self.bucket_name}/{key}"
```

2. **Update Service Interface**
```python
class IDocumentStorageService(Protocol):
    def save_pdf(self, pdf_bytes: bytes, path: str) -> str: ...
    def load_pdf(self, path: str) -> bytes: ...
    def delete_pdf(self, path: str) -> None: ...
```

3. **Dependency Injection**
```python
# In container/factory
if settings.USE_CLOUD_STORAGE:
    storage_service = CloudStorageService(s3_client, settings.S3_BUCKET)
else:
    storage_service = DocumentStorageService(base_storage_path="storage/documents")
```

4. **Database Migration**
- Update `documents` table `file_path` column to store S3 URLs
- Migrate existing PDFs to S3
- Update paths in database

### Benefits of Abstraction

- **Zero API Changes**: Frontend and business logic unaffected
- **Environment-Specific**: Use filesystem locally, S3 in production
- **Easy Rollback**: Switch back to filesystem if needed
- **Testing**: Mock storage service for unit tests

---

## Testing

### Unit Tests

```python
def test_pdf_generation_service():
    service = PDFGenerationService()
    assert service.available == WEASYPRINT_AVAILABLE
    
    if service.available:
        html = "<html><body>Test</body></html>"
        pdf = service.generate_pdf_from_html(html)
        assert len(pdf) > 0
```

### Integration Tests

```python
def test_document_generation_endpoint(client):
    response = client.post(
        "/api/v1/documents/work_order/123/generate",
        headers={"Authorization": "Bearer token"}
    )
    assert response.status_code == 200
    assert "id" in response.json()
```

### Manual Testing

```bash
# Test WeasyPrint availability
curl http://localhost:8000/api/v1/documents/test/pdf

# Generate specific document
curl -X POST http://localhost:8000/api/v1/documents/work_order/{id}/generate \
  -H "Authorization: Bearer token"

# Download generated PDF
curl http://localhost:8000/api/v1/documents/{doc_id}/download \
  -H "Authorization: Bearer token" \
  --output test.pdf
```

---

## Performance Considerations

### PDF Generation Time

- Simple documents: ~100-500ms
- Complex documents (many tables, images): ~500-2000ms
- First generation slower (template compilation)
- Subsequent generations faster (cached templates)

### Caching

Templates are compiled by Jinja2 and cached. Consider:
- Template-level caching (Jinja2 built-in)
- Document-level caching (if content doesn't change)
- CDN for PDF downloads (future enhancement)

### Storage Growth

Monitor storage usage:
```bash
du -sh /app/storage/documents
```

Consider cleanup strategy:
- Archive old documents (e.g., > 1 year)
- Compress archived PDFs
- Move to cold storage (S3 Glacier)

---

## Security Considerations

### Tenant Isolation

- PDFs stored in tenant-specific directories
- File paths include tenant_id
- API endpoints enforce tenant_id from JWT

### Access Control

- Document generation requires authentication
- Download/preview endpoints check document ownership
- No direct filesystem access from API

### Path Traversal Prevention

- Use `pathlib.Path` for safe path operations
- Validate entity_id is valid UUID
- Never use user input in file paths directly

---

## Summary

- **WeasyPrint** provides enterprise-grade PDF generation
- **Docker** ensures consistent environment with pre-installed dependencies
- **Graceful fallback** allows backend to start without PDF features
- **Storage abstraction** enables future S3/cloud migration
- **Render.com compatible** out-of-the-box
- **Windows development** possible via Docker or GTK installation

For quick setup, see [README.md](../README.md#pdf-generation).
