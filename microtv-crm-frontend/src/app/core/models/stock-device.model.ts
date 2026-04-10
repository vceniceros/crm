export interface StockDeviceOption {
  id: number | string;
  code?: string;
  name: string;
  category?: string;
  serial?: string;
}

export interface StockDevicesMockData {
  devices: StockDeviceOption[];
}