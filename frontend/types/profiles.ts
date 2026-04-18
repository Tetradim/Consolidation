export interface BrokerSettingsData {
  broker_id: string;
  enabled: boolean;
  auto_trading_enabled: boolean;
  alerts_only: boolean;
  premium_buffer_enabled: boolean;
  take_profit_enabled: boolean;
  take_profit_percentage: number;
  bracket_order_enabled: boolean;
  stop_loss_enabled: boolean;
  stop_loss_percentage: number;
  trailing_stop_enabled: boolean;
  trailing_stop_percent: number;
  averaging_down_enabled: boolean;
  auto_shutdown_enabled: boolean;
  max_consecutive_losses: number;
}

export interface Broker {
  id: string;
  name: string;
  description: string;
}

export interface Profile {
  id: string;
  name: string;
  description: string;
  active_brokers: string[];
  created_at: string;
  is_active: boolean;
}
