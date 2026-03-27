/**
 * Client Form Page
 * Create or edit a sales client
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FormSkeleton } from '@/components/shared/LoadingSkeleton';
import { clientsApi } from '@/services/sales.service';
import { SalesClient, CreateClientRequest } from '@/types/sales.types';
import { ArrowLeft, Save } from 'lucide-react';

export default function ClientFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = !!id;

  const [formData, setFormData] = useState<Partial<SalesClient> & CreateClientRequest>({
    code: '',
    name: '',
    email: '',
    phone: '',
    address: '',
    gst_number: '',
    credit_limit: 0,
    payment_terms_days: 0,
  });
  const [loading, setLoading] = useState(isEditing);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const loadClient = async () => {
      if (!isEditing || !id) return;

      try {
        setError(null);
        const client = await clientsApi.get(id);
        setFormData(client);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load client');
      } finally {
        setLoading(false);
      }
    };

    loadClient();
  }, [isEditing, id]);

  const handleSave = async () => {
    setSaving(true);
    try {
      if (isEditing && id) {
        await clientsApi.update(id, {
          name: formData.name,
          email: formData.email,
          phone: formData.phone,
          address: formData.address,
          gst_number: formData.gst_number,
          credit_limit: formData.credit_limit,
          payment_terms_days: formData.payment_terms_days,
        });
      } else {
        await clientsApi.create({
          code: formData.code || '',
          name: formData.name || '',
          email: formData.email,
          phone: formData.phone,
          address: formData.address,
          gst_number: formData.gst_number,
          credit_limit: formData.credit_limit || 0,
          payment_terms_days: formData.payment_terms_days || 0,
        });
      }
      navigate('/sales/clients');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save client');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <FormSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/sales/clients')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditing ? 'Edit Client' : 'Add New Client'}
          </h1>
          <p className="text-gray-600">{isEditing ? 'Update client details' : 'Register a new sales client'}</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Client Form */}
      <Card>
        <CardHeader>
          <CardTitle>Client Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Code */}
          {!isEditing && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Client Code *</label>
              <Input
                placeholder="e.g., CLI001"
                value={formData.code || ''}
                onChange={(e) => setFormData({...formData, code: e.target.value})}
              />
            </div>
          )}

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Client Name *</label>
            <Input
              placeholder="Full client name"
              value={formData.name || ''}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
            />
          </div>

          {/* Contact Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <Input
                type="email"
                placeholder="client@example.com"
                value={formData.email || ''}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Phone</label>
              <Input
                placeholder="+1 (555) 123-4567"
                value={formData.phone || ''}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
              />
            </div>
          </div>

          {/* Address */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Address</label>
            <Textarea
              placeholder="Full address"
              value={formData.address || ''}
              onChange={(e) => setFormData({...formData, address: e.target.value})}
              rows={3}
            />
          </div>

          {/* GST & Payment */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">GST Number</label>
              <Input
                placeholder="GST ID"
                value={formData.gst_number || ''}
                onChange={(e) => setFormData({...formData, gst_number: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Payment Terms (Days)</label>
              <Input
                type="number"
                placeholder="30"
                value={formData.payment_terms_days || 0}
                onChange={(e) => setFormData({...formData, payment_terms_days: parseInt(e.target.value)})}
              />
            </div>
          </div>

          {/* Credit Limit */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Credit Limit *</label>
            <Input
              type="number"
              placeholder="10000"
              value={formData.credit_limit || 0}
              onChange={(e) => setFormData({...formData, credit_limit: parseFloat(e.target.value)})}
            />
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-3 justify-end">
        <Button variant="outline" onClick={() => navigate('/sales/clients')}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700">
          <Save className="mr-2 h-4 w-4" />
          {saving ? 'Saving...' : 'Save Client'}
        </Button>
      </div>
    </div>
  );
}
