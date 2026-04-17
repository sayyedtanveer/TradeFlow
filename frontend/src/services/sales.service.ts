/**
 * Sales API Service
 * Handles all API calls for Sales Orders, Clients, and Price Lists
 */

import { apiClient } from './api-client';
import {
  SalesClient,
  SalesOrder,
  PriceList,
  OrderStatus,
  CreateClientRequest,
  UpdateClientRequest,
  CreateOrderRequest,
  UpdateOrderRequest,
  CreateOrderLineRequest,
  CreatePriceListRequest,
  ClientCreditInfo,
  OrderStatistics,
  SalesListResponse,
} from '@/types/sales.types';

const BASE_URL = '/sales';

/**
 * ============================================================================
 * CLIENTS API
 * ============================================================================
 */

export const clientsApi = {
  /**
   * Create a new sales client
   */
  create: async (data: CreateClientRequest): Promise<SalesClient> => {
    return apiClient.post(`${BASE_URL}/clients`, data);
  },

  /**
   * Get client by ID
   */
  get: async (clientId: string): Promise<SalesClient> => {
    return apiClient.get(`${BASE_URL}/clients/${clientId}`);
  },

  /**
   * List all clients with pagination and filtering
   */
  list: async (
    limit?: number,
    offset?: number,
    search?: string,
    is_active?: boolean
  ): Promise<SalesListResponse<SalesClient>> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    if (search) params.append('search', search);
    if (is_active !== undefined) params.append('is_active', is_active.toString());

    const query = params.toString();
    return apiClient.get(`${BASE_URL}/clients${query ? `?${query}` : ''}`);
  },

  /**
   * Update client
   */
  update: async (clientId: string, data: UpdateClientRequest): Promise<SalesClient> => {
    return apiClient.patch(`${BASE_URL}/clients/${clientId}`, data);
  },

  /**
   * Deactivate (soft delete) client
   */
  deactivate: async (clientId: string): Promise<void> => {
    return apiClient.delete(`${BASE_URL}/clients/${clientId}`);
  },

  /**
   * Get client credit information
   */
  getCredit: async (clientId: string): Promise<ClientCreditInfo> => {
    return apiClient.get(`${BASE_URL}/clients/${clientId}/credit`);
  },
};

/**
 * ============================================================================
 * SALES ORDERS API
 * ============================================================================
 */

export const ordersApi = {
  /**
   * Create a new sales order
   */
  create: async (data: CreateOrderRequest): Promise<SalesOrder> => {
    return apiClient.post(`${BASE_URL}/orders`, data);
  },

  /**
   * Get sales order by ID (with full details)
   */
  get: async (orderId: string): Promise<SalesOrder> => {
    return apiClient.get(`${BASE_URL}/orders/${orderId}`);
  },

  /**
   * Get sales order by order number
   */
  getByNumber: async (orderNumber: string): Promise<SalesOrder> => {
    return apiClient.get(`${BASE_URL}/orders/number/${orderNumber}`);
  },

  /**
   * List all sales orders with filtering
   */
  list: async (
    limit?: number,
    offset?: number,
    clientId?: string,
    status?: OrderStatus,
    startDate?: string,
    endDate?: string
  ): Promise<SalesListResponse<SalesOrder>> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    if (clientId) params.append('client_id', clientId);
    if (status) params.append('status', status);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const query = params.toString();
    return apiClient.get(`${BASE_URL}/orders${query ? `?${query}` : ''}`);
  },

  /**
   * Update sales order (before confirmation)
   */
  update: async (orderId: string, data: UpdateOrderRequest): Promise<SalesOrder> => {
    return apiClient.patch(`${BASE_URL}/orders/${orderId}`, data);
  },

  /**
   * List draft orders waiting for confirmation
   */
  listDraft: async (limit?: number): Promise<SalesListResponse<SalesOrder>> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    const query = params.toString();
    return apiClient.get(`${BASE_URL}/orders/draft${query ? `?${query}` : ''}`);
  },

  /**
   * Add line item to order
   */
  addLine: async (orderId: string, line: CreateOrderLineRequest): Promise<SalesOrder> => {
    return apiClient.post(`${BASE_URL}/orders/${orderId}/lines`, line);
  },

  /**
   * Remove line item from order
   */
  removeLine: async (orderId: string, lineId: string): Promise<SalesOrder> => {
    return apiClient.delete(`${BASE_URL}/orders/${orderId}/lines/${lineId}`);
  },

  /**
   * Apply discount to order
   */
  applyDiscount: async (orderId: string, discountAmount: number): Promise<SalesOrder> => {
    return apiClient.post(`${BASE_URL}/orders/${orderId}/discount`, {
      discount_amount: discountAmount,
    });
  },

  /**
   * Confirm order (move from DRAFT to CONFIRMED)
   */
  confirm: async (orderId: string): Promise<SalesOrder> => {
    return apiClient.post(`${BASE_URL}/orders/${orderId}/confirm`, {});
  },

  /**
   * Record shipment (move to SHIPPED)
   */
  ship: async (orderId: string, shipmentData?: any): Promise<SalesOrder> => {
    return apiClient.post(`${BASE_URL}/orders/${orderId}/ship`, shipmentData || {});
  },

  /**
   * Record delivery (move to DELIVERED)
   */
  deliver: async (orderId: string, deliveryData?: any): Promise<SalesOrder> => {
    return apiClient.post(`${BASE_URL}/orders/${orderId}/deliver`, deliveryData || {});
  },

  /**
   * Cancel order
   */
  cancel: async (orderId: string, reason?: string): Promise<SalesOrder> => {
    return apiClient.post(`${BASE_URL}/orders/${orderId}/cancel`, { reason });
  },

  /**
   * Get order statistics (count by status)
   */
  getStatistics: async (): Promise<OrderStatistics> => {
    return apiClient.get(`${BASE_URL}/orders/stats/by-status`);
  },
};

/**
 * ============================================================================
 * PRICE LISTS API
 * ============================================================================
 */

export const priceListsApi = {
  /**
   * Create a new price list
   */
  create: async (data: CreatePriceListRequest): Promise<PriceList> => {
    return apiClient.post(`${BASE_URL}/price-lists`, data);
  },

  /**
   * Get price list by ID
   */
  get: async (priceListId: string): Promise<PriceList> => {
    return apiClient.get(`${BASE_URL}/price-lists/${priceListId}`);
  },

  /**
   * List all price lists
   */
  list: async (limit?: number, offset?: number): Promise<SalesListResponse<PriceList>> => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());

    const query = params.toString();
    return apiClient.get(`${BASE_URL}/price-lists${query ? `?${query}` : ''}`);
  },

  /**
   * Update price list
   */
  update: async (
    priceListId: string,
    data: Partial<CreatePriceListRequest>
  ): Promise<PriceList> => {
    return apiClient.patch(`${BASE_URL}/price-lists/${priceListId}`, data);
  },

  /**
   * Add line to price list
   */
  addLine: async (priceListId: string, lineData: any): Promise<PriceList> => {
    return apiClient.post(`${BASE_URL}/price-lists/${priceListId}/lines`, lineData);
  },

  /**
   * Update price list line
   */
  updateLine: async (priceListId: string, lineData: any): Promise<PriceList> => {
    return apiClient.patch(`${BASE_URL}/price-lists/${priceListId}/lines`, lineData);
  },

  /**
   * Remove line from price list
   */
  removeLine: async (priceListId: string, lineId: string): Promise<PriceList> => {
    return apiClient.delete(`${BASE_URL}/price-lists/${priceListId}/lines/${lineId}`);
  },
};

/**
 * Export all sales API methods
 */
export const salesApi = {
  clients: clientsApi,
  orders: ordersApi,
  priceLists: priceListsApi,
};

export default salesApi;
