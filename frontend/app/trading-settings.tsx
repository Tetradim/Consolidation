/**
 * Trading Settings Page
 * 
 * Dedicated page for trading configuration
 */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export function TradingSettingsPage() {
  const [settings, setSettings] = useState({
    // Trading Mode
    simulationMode: true,
    autoTradingEnabled: true,
    
    // Price Buffer
    priceBufferEnabled: true,
    priceBufferPercentage: 3.0,
    
    // Orders
    orderTimeout: 30,
    retryFilledCheck: true,
    retryInterval: 2,
    
    // Broker
    activeBroker: 'IBKR',
    brokerGatewayUrl: 'https://localhost:5000',
    brokerAccountId: '',
    
    // Execution
    orderType: 'LIMIT',
  });

  const updateSetting = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="w-full max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Trading Settings</h1>

      {/* Trading Mode */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Trading Mode</CardTitle>
          <CardDescription>Configure how trades are executed</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>Simulation Mode</Label>
              <p className="text-sm text-gray-500">Paper trading - no real money</p>
            </div>
            <Switch
              checked={settings.simulationMode}
              onCheckedChange={(checked) => updateSetting('simulationMode', checked)}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <Label>Auto Trading</Label>
              <p className="text-sm text-gray-500">Automatically execute alerts</p>
            </div>
            <Switch
              checked={settings.autoTradingEnabled}
              onCheckedChange={(checked) => updateSetting('autoTradingEnabled', checked)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Price Buffer */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Price Buffer</CardTitle>
          <CardDescription>Safety margin for order prices</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Enable Buffer</Label>
            <Switch
              checked={settings.priceBufferEnabled}
              onCheckedChange={(checked) => updateSetting('priceBufferEnabled', checked)}
            />
          </div>
          
          <div>
            <Label>Buffer: {settings.priceBufferPercentage}%</Label>
            <Slider
              value={[settings.priceBufferPercentage]}
              onValueChange={([val]) => updateSetting('priceBufferPercentage', val)}
              min={0}
              max={10}
              step={0.5}
            />
            <p className="text-sm text-gray-500 mt-1">
              Order will be placed at {100 - settings.priceBufferPercentage}% of alert price
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Broker */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Broker Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Active Broker</Label>
            <Select
              value={settings.activeBroker}
              onValueChange={(val) => updateSetting('activeBroker', val)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="IBKR">Interactive Brokers</SelectItem>
                <SelectItem value="ALPACA">Alpaca</SelectItem>
                <SelectItem value="TRADIER">Tradier</SelectItem>
                <SelectItem value="TD">TD Ameritrade</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <Label>Gateway URL</Label>
            <Input
              value={settings.brokerGatewayUrl}
              onChange={(e) => updateSetting('brokerGatewayUrl', e.target.value)}
              placeholder="https://localhost:5000"
            />
          </div>
          
          <div>
            <Label>Account ID</Label>
            <Input
              value={settings.brokerAccountId}
              onChange={(e) => updateSetting('brokerAccountId', e.target.value)}
              placeholder="your-account-id"
            />
          </div>
          
          <div>
            <Label>Order Type</Label>
            <Select
              value={settings.orderType}
              onValueChange={(val) => updateSetting('orderType', val)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="MARKET">Market</SelectItem>
                <SelectItem value="LIMIT">Limit</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Order Settings */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Order Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Timeout (seconds)</Label>
              <Input
                type="number"
                value={settings.orderTimeout}
                onChange={(e) => updateSetting('orderTimeout', Number(e.target.value))}
              />
            </div>
            <div>
              <Label>Retry Interval (seconds)</Label>
              <Input
                type="number"
                value={settings.retryInterval}
                onChange={(e) => updateSetting('retryInterval', Number(e.target.value))}
              />
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <Label>Check for Fill</Label>
            <Switch
              checked={settings.retryFilledCheck}
              onCheckedChange={(checked) => updateSetting('retryFilledCheck', checked)}
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button variant="outline">Reset</Button>
        <Button>Save Settings</Button>
      </div>
    </div>
  );
}