import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'

export interface Document {
  id: string
  tenant_id: string
  document_type: string
  entity_id: string
  version_number: number
  file_path: string
  generated_by: string | null
  generated_at: string
  is_deleted: boolean
  deleted_at: string | null
}

export interface DocumentVersion {
  id: string
  version_number: number
  generated_by: string | null
  generated_at: string
  file_path: string
}

export interface DocumentList {
  document_type: string
  entity_id: string
  versions: DocumentVersion[]
  total: number
}

export interface DocumentGenerateOptions {
  force_regenerate?: boolean
}

class DocumentService {
  private getHeaders() {
    const token = localStorage.getItem('access_token')
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    }
  }

  async generateDocument(
    documentType: string,
    entityId: string,
    options: DocumentGenerateOptions = {}
  ): Promise<Document> {
    const response = await axios.post(
      `${API_BASE}/documents/${documentType}/${entityId}/generate`,
      options,
      { headers: this.getHeaders() }
    )
    return response.data
  }

  async downloadDocument(documentId: string): Promise<Blob> {
    const response = await axios.get(
      `${API_BASE}/documents/${documentId}/download`,
      {
        headers: this.getHeaders(),
        responseType: 'blob',
      }
    )
    return response.data
  }

  async downloadDocumentByUrl(documentId: string, filename?: string): Promise<void> {
    const blob = await this.downloadDocument(documentId)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || `document_${documentId}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  async listDocumentVersions(
    documentType: string,
    entityId: string
  ): Promise<DocumentList> {
    const response = await axios.get(
      `${API_BASE}/documents/${documentType}/${entityId}/versions`,
      { headers: this.getHeaders() }
    )
    return response.data
  }

  async previewDocument(documentId: string): Promise<string> {
    const blob = await this.downloadDocument(documentId)
    const url = window.URL.createObjectURL(blob)
    return url
  }
}

export const documentService = new DocumentService()
