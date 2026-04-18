/**
 * Risk Management Settings Tabs Component
 * 
 * Tabbed interface for all risk management settings
 * - Position Sizing
 * - Stop Loss
 * - Take Profit
 * - Trailing Stop  
 * - Auto Shutdown
 * - Correlation
 */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export function RiskSettingsTabs() {
  const [settings, setSettings] = useState({
    // Position Sizing
    maxPositionSize: 1000,
    defaultQuantity: 1,
    riskPerTrade: 1.0,
    
    // Stop Loss
    stopLossEnabled: true,
    stopLossPercentage: 30,
    stopLossOrderType: 'market',
    
    // Take Profit
    takeProfitEnabled: true,
    takeProfitPercentage: 50,
    multiLevelTakeProfit: false,
    profitLevels: [
      { percentage: 25, sellPercentage: 33 },
      { percentage: 50, sellPercentage: 67 },
    ],
    
    // Trailing Stop
    trailingStopEnabled: true,
    trailingStopType: 'percent',
    trailingStopPercent: 25,
    trailingStopCents: 0.25,
    
    // Auto Shutdown
    autoShutdownEnabled: true,
    maxConsecutiveLosses: 3,
    maxDailyLosses: 5,
    maxDailyLossAmount: 500,
    maxDrawdownPercent: 20,
    
    // Correlation
    maxPositionsPerTicker: 3,
    maxPositionsPerSector: 3,
  });

  const updateSetting = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Risk Management</h1>
      
      <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
        <button 
          className="px-4 py-2 bg-blue-600 text-white rounded"
          onClick={() => document.getElementById('position-tab')?.scrollIntoView()}
        >
          Position
        </button>
        <button 
          className="px-4 py-2 bg-gray-200 rounded"
          onClick={() => document.getElementById('stoploss-tab')?.scrollIntoView()}
        >
          Stop Loss
        </button>
        <button 
          className="px-4 py-2 bg-gray-200 rounded"
          onClick={() => document.getElementById('takeprofit-tab')?.scrollIntoView()}
        >
          Take Profit
        </button>
        <button 
          className="px-4 py-2 bg-gray-200 rounded"
          onClick={() => document.getElementById('trailing-tab')?.scrollIntoView()}
        >
          Trailing
        </button>
        <button 
          className="px-4 py-2 bg-gray-200 rounded"
          onClick={() => document.getElementById('shutdown-tab')?.scrollIntoView()}
        >
          Shutdown
        </button>
        <button 
          className="px-4 py-2 bg-gray-200 rounded"
          onClick={() => document.getElementById('correlation-tab')?.scrollIntoView()}
        >
          Correlation
        </button>
      </div>

      {/* Position Sizing Tab */}
      <div id="position-tab" className="mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Position Sizing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Max Position Size ($)</Label>
                <Input
                  type="number"
                  value={settings.maxPositionSize}
                  onChange={(e) => updateSetting('maxPositionSize', Number(e.target.value))}
                />
              </div>
              <div>
                <Label>Default Quantity</Label>
                <Input
                  type="number"
                  value={settings.defaultQuantity}
                  onChange={(e) => updateSetting('defaultQuantity', Number(e.target.value))}
                />
              </div>
            </div>
            
            <div>
              <Label>Risk Per Trade: {settings.riskPerTrade.toFixed(1)}%</Label>
              <Slider
                value={[settings.riskPerTrade * 100]}
                onValueChange={([val]) => updateSetting('riskPerTrade', val / 100)}
                max={5}
                step={0.5}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stop Loss Tab */}
      <div id="stoploss-tab" className="mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Stop Loss</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Enable Stop Loss</Label>
              <Switch
                checked={settings.stopLossEnabled}
                onCheckedChange={(checked) => updateSetting('stopLossEnabled', checked)}
              />
            </div>
            
            <div>
              <Label>Stop Loss: {settings.stopLossPercentage}%</Label>
              <Slider
                value={[settings.stopLossPercentage]}
                onValueChange={([val]) => updateSetting('stopLossPercentage', val)}
                min={5}
                max={50}
                step={5}
              />
            </div>
            
            <div>
              <Label>Order Type</Label>
              <Select
                value={settings.stopLossOrderType}
                onValueChange={(val) => updateSetting('stopLossOrderType', val)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="market">Market Order</SelectItem>
                  <SelectItem value="limit">Limit Order</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Take Profit Tab */}
      <div id="takeprofit-tab" className="mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Take Profit</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Enable Take Profit</Label>
              <Switch
                checked={settings.takeProfitEnabled}
                onCheckedChange={(checked) => updateSetting('takeProfitEnabled', checked)}
              />
            </div>
            
            <div>
              <Label>Profit Target: {settings.takeProfitPercentage}%</Label>
              <Slider
                value={[settings.takeProfitPercentage]}
                onValueChange={([val]) => updateSetting('takeProfitPercentage', val)}
                min={10}
                max={100}
                step={5}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <Label>Multi-Level Take Profit</Label>
              <Switch
                checked={settings.multiLevelTakeProfit}
                onCheckedChange={(checked) => updateSetting('multiLevelTakeProfit', checked)}
              />
            </div>
            
            {settings.multiLevelTakeProfit && (
              <div className="p-4 bg-gray-100 rounded-lg space-y-2">
                <Label className="font-medium">Profit Levels</Label>
                {settings.profitLevels.map((level, idx) => (
                  <div key={idx} className="flex gap-2">
                    <span className="w-20">{level.percentage}% → sell {level.sellPercentage}%</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Trailing Stop Tab */}
      <div id="trailing-tab" className="mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Trailing Stop</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Enable Trailing Stop</Label>
              <Switch
                checked={settings.trailingStopEnabled}
                onCheckedChange={(checked) => updateSetting('trailingStopEnabled', checked)}
              />
            </div>
            
            <div>
              <Label>Trailing Type</Label>
              <Select
                value={settings.trailingStopType}
                onValueChange={(val) => updateSetting('trailingStopType', val)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="percent">Percentage Trail</SelectItem>
                  <SelectItem value="premium">Cents/Premium Trail</SelectItem>
                  <SelectItem value="atr">ATR Based</SelectItem>
                  <SelectItem value="time">Time Based</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {settings.trailingStopType === 'percent' && (
              <div>
                <Label>Trail Distance: {settings.trailingStopPercent}%</Label>
                <Slider
                  value={[settings.trailingStopPercent]}
                  onValueChange={([val]) => updateSetting('trailingStopPercent', val)}
                  min={5}
                  max={50}
                  step={5}
                />
              </div>
            )}
            
            {settings.trailingStopType === 'premium' && (
              <div>
                <Label>Trail Cents</Label>
                <Input
                  type="number"
                  step="0.05"
                  value={settings.trailingStopCents}
                  onChange={(e) => updateSetting('trailingStopCents', Number(e.target.value))}
                />
              </div>
            )}
            
            {settings.trailingStopType === 'time' && (
              <div>
                <Label>Hours Until Exit</Label>
                <Input type="number" value={4} readOnly />
                <span className="text-sm text-gray-500 ml-2">hours</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Auto Shutdown Tab */}
      <div id="shutdown-tab" className="mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Auto Shutdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Enable Auto Shutdown</Label>
              <Switch
                checked={settings.autoShutdownEnabled}
                onCheckedChange={(checked) => updateSetting('autoShutdownEnabled', checked)}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Max Consecutive Losses</Label>
                <Input
                  type="number"
                  value={settings.maxConsecutiveLosses}
                  onChange={(e) => updateSetting('maxConsecutiveLosses', Number(e.target.value))}
                />
              </div>
              <div>
                <Label>Max Daily Losses</Label>
                <Input
                  type="number"
                  value={settings.maxDailyLosses}
                  onChange={(e) => updateSetting('maxDailyLosses', Number(e.target.value))}
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Max Daily Loss ($)</Label>
                <Input
                  type="number"
                  value={settings.maxDailyLossAmount}
                  onChange={(e) => updateSetting('maxDailyLossAmount', Number(e.target.value))}
                />
              </div>
              <div>
                <Label>Max Drawdown (%)</Label>
                <Input
                  type="number"
                  value={settings.maxDrawdownPercent}
                  onChange={(e) => updateSetting('maxDrawdownPercent', Number(e.target.value))}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Correlation Tab */}
      <div id="correlation-tab" className="mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Correlation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Max Positions Per Ticker</Label>
                <Input
                  type="number"
                  value={settings.maxPositionsPerTicker}
                  onChange={(e) => updateSetting('maxPositionsPerTicker', Number(e.target.value))}
                />
              </div>
              <div>
                <Label>Max Positions Per Sector</Label>
                <Input
                  type="number"
                  value={settings.maxPositionsPerSector}
                  onChange={(e) => updateSetting('maxPositionsPerSector', Number(e.target.value))}
                />
              </div>
            </div>
            
            <div className="p-4 bg-gray-100 rounded-lg">
              <Label className="font-medium">Sector Mapping</Label>
              <p className="text-sm text-gray-500 mt-1">
                QQQ, AAPL, MSFT, NVDA → Tech | BAC, JPM → Finance | XOM, CVX → Energy | AMZN → Consumer
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 flex justify-end">
        <Button>Save Risk Settings</Button>
      </div>
    </div>
  );
}