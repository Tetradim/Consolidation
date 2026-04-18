/**
 * Risk Management Settings Page
 * 
 * Complete risk management configuration page
 */
import React, { useState } from 'react';
import { View, Text, TextInput, Switch, Button, ScrollView, TouchableOpacity } from 'react-native';

type TabType = 'position' | 'stoploss' | 'takeprofit' | 'trailing' | 'shutdown' | 'correlation';

export function RiskSettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('position');
  
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
    
    // Trailing Stop
    trailingStopEnabled: true,
    trailingStopType: 'percent',
    trailingStopPercent: 25,
    trailingStopCents: 0.25,
    trailingHours: 4,
    
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

  const tabs: { id: TabType; label: string }[] = [
    { id: 'position', label: 'Position' },
    { id: 'stoploss', label: 'Stop Loss' },
    { id: 'takeprofit', label: 'Take Profit' },
    { id: 'trailing', label: 'Trailing' },
    { id: 'shutdown', label: 'Shutdown' },
    { id: 'correlation', label: 'Correlation' },
  ];

  return (
    <div className="w-full max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Risk Management</h1>
      
      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 mb-6 pb-2 border-b">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Position Sizing Tab */}
      {activeTab === 'position' && (
        <Card>
          <CardHeader>
            <CardTitle>Position Sizing</CardTitle>
            <CardDescription>Configure position size limits</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Max Position Size ($)</Label>
                <Input
                  type="number"
                  value={settings.maxPositionSize}
                  onChange={(e) => updateSetting('maxPositionSize', Number(e.target.value))}
                />
                <p className="text-xs text-gray-500 mt-1">Maximum $ per position</p>
              </div>
              <div>
                <Label>Default Quantity</Label>
                <Input
                  type="number"
                  value={settings.defaultQuantity}
                  onChange={(e) => updateSetting('defaultQuantity', Number(e.target.value))}
                />
                <p className="text-xs text-gray-500 mt-1">Contracts per trade</p>
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
              <p className="text-xs text-gray-500 mt-1">% of capital at risk per trade</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stop Loss Tab */}
      {activeTab === 'stoploss' && (
        <Card>
          <CardHeader>
            <CardTitle>Stop Loss</CardTitle>
            <CardDescription>Configure stop loss exit</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label>Enable Stop Loss</Label>
                <p className="text-sm text-gray-500">Auto-exit when loss threshold hit</p>
              </div>
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
              <p className="text-xs text-gray-500 mt-1">Exit at this % below entry</p>
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
                  <SelectItem value="market">Market Order (immediate)</SelectItem>
                  <SelectItem value="limit">Limit Order (price improvement)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Take Profit Tab */}
      {activeTab === 'takeprofit' && (
        <Card>
          <CardHeader>
            <CardTitle>Take Profit</CardTitle>
            <CardDescription>Configure profit taking exits</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label>Enable Take Profit</Label>
                <p className="text-sm text-gray-500">Auto-exit when profit target hit</p>
              </div>
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
              <p className="text-xs text-gray-500 mt-1">Exit at this % above entry</p>
            </div>
            
            <div className="flex items-center justify-between">
              <div>
                <Label>Multi-Level</Label>
                <p className="text-sm text-gray-500">Multiple profit targets</p>
              </div>
              <Switch
                checked={settings.multiLevelTakeProfit}
                onCheckedChange={(checked) => updateSetting('multiLevelTakeProfit', checked)}
              />
            </div>
            
            {settings.multiLevelTakeProfit && (
              <div className="p-4 bg-gray-100 rounded-lg">
                <p className="font-medium mb-2">Profit Levels</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>50% profit →</span>
                    <span className="text-green-600">Sell 50%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>100% profit →</span>
                    <span className="text-green-600">Sell remaining</span>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Trailing Stop Tab */}
      {activeTab === 'trailing' && (
        <Card>
          <CardHeader>
            <CardTitle>Trailing Stop</CardTitle>
            <CardDescription>Dynamic stop that moves with price</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label>Enable Trailing Stop</Label>
                <p className="text-sm text-gray-500">Move stop with price</p>
              </div>
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
                  <SelectItem value="percent">Percentage</SelectItem>
                  <SelectItem value="premium">Cents/Premium</SelectItem>
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
                <p className="text-xs text-gray-500 mt-1">Stop trails this % below peak</p>
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
                <p className="text-xs text-gray-500 mt-1">Stop trails this $ below peak</p>
              </div>
            )}
            
            {settings.trailingStopType === 'time' && (
              <div>
                <Label>Hours Until Exit</Label>
                <Input
                  type="number"
                  value={settings.trailingHours}
                  onChange={(e) => updateSetting('trailingHours', Number(e.target.value))}
                />
                <p className="text-xs text-gray-500 mt-1">Auto-exit after this many hours</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Auto Shutdown Tab */}
      {activeTab === 'shutdown' && (
        <Card>
          <CardHeader>
            <CardTitle>Auto Shutdown</CardTitle>
            <CardDescription>Stop trading on loss thresholds</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label>Enable Auto Shutdown</Label>
                <p className="text-sm text-gray-500">Pause trading on limits</p>
              </div>
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
                <p className="text-xs text-gray-500 mt-1">Stop after X losses in a row</p>
              </div>
              <div>
                <Label>Max Daily Losses</Label>
                <Input
                  type="number"
                  value={settings.maxDailyLosses}
                  onChange={(e) => updateSetting('maxDailyLosses', Number(e.target.value))}
                />
                <p className="text-xs text-gray-500 mt-1">Stop after X losses today</p>
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
                <p className="text-xs text-gray-500 mt-1">Stop after $X loss today</p>
              </div>
              <div>
                <Label>Max Drawdown (%)</Label>
                <Input
                  type="number"
                  value={settings.maxDrawdownPercent}
                  onChange={(e) => updateSetting('maxDrawdownPercent', Number(e.target.value))}
                />
                <p className="text-xs text-gray-500 mt-1">Stop after X% drop</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Correlation Tab */}
      {activeTab === 'correlation' && (
        <Card>
          <CardHeader>
            <CardTitle>Correlation</CardTitle>
            <CardDescription>Avoid over-concentration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Max Positions Per Ticker</Label>
                <Input
                  type="number"
                  value={settings.maxPositionsPerTicker}
                  onChange={(e) => updateSetting('maxPositionsPerTicker', Number(e.target.value))}
                />
                <p className="text-xs text-gray-500 mt-1">Max positions in same stock</p>
              </div>
              <div>
                <Label>Max Positions Per Sector</Label>
                <Input
                  type="number"
                  value={settings.maxPositionsPerSector}
                  onChange={(e) => updateSetting('maxPositionsPerSector', Number(e.target.value))}
                />
                <p className="text-xs text-gray-500 mt-1">Max positions in same sector</p>
              </div>
            </div>
            
            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="font-medium mb-2">Sector Mapping</p>
              <div className="text-sm text-gray-600 grid grid-cols-2 gap-1">
                <span>Tech: QQQ, AAPL, MSFT, GOOGL, NVDA</span>
                <span>Finance: JPM, BAC, WFC, GS</span>
                <span>Energy: XOM, CVX, COP</span>
                <span>Consumer: AMZN, WMT, HD</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mt-6 flex justify-end gap-2">
        <Button variant="outline">Reset</Button>
        <Button>Save Risk Settings</Button>
      </div>
    </div>
  );
}