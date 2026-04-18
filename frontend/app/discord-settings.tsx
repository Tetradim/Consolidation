/**
 * Discord Communities Settings Page
 * 
 * Configure multiple Discord communities with custom alert patterns
 */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

type TabType = 'communities' | 'patterns' | 'filters';

export function DiscordSettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('communities');
  
  const [communities, setCommunities] = useState([
    {
      id: '1',
      name: 'Main Trading Server',
      channelId: '123456789',
      enabled: true,
      preset: 'default',
      autoTrade: false,
      simulation: true,
    }
  ]);
  
  const [patterns, setPatterns] = useState({
    buyKeywords: 'BUY,ENTRY,LONG,BTO,OPENING',
    sellKeywords: 'SELL,EXIT,CLOSE,STC,TRIM',
    avgDownKeywords: 'AVERAGE DOWN,AVG DOWN,AVERAGING,ADD TO',
    ignoreKeywords: 'WATCHLIST,WATCHING,MIGHT,PAPER',
    tickerPattern: r'\$([A-Z]{1,5})\b',
    requireTicker: true,
    requireExpiration: true,
    requirePrice: true,
  });
  
  const [filters, setFilters] = useState({
    listenToUsers: '',
    ignoreUsers: '',
    listenToChannels: '',
    minPrice: 0.01,
    maxPrice: 100,
  });

  const presets = [
    { id: 'default', name: 'Default' },
    { id: 'aggressive', name: 'Aggressive Trading' },
    { id: 'swing', name: 'Swing Trading' },
    { id: 'theta', name: 'Theta Gang' },
    { id: 'momentum', name: 'Momentum' },
    { id: 'custom', name: 'Custom' },
  ];

  const addCommunity = () => {
    setCommunities([...communities, {
      id: Date.now().toString(),
      name: 'New Community',
      channelId: '',
      enabled: true,
      preset: 'default',
      autoTrade: false,
      simulation: true,
    }]);
  };

  const updateCommunity = (id: string, field: string, value: any) => {
    setCommunities(communities.map(c => 
      c.id === id ? { ...c, [field]: value } : c
    ));
  };

  const removeCommunity = (id: string) => {
    setCommunities(communities.filter(c => c.id !== id));
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Discord Configuration</h1>
      
      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('communities')}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'communities' ? 'bg-blue-600 text-white' : 'bg-gray-200'
          }`}
        >
          Communities
        </button>
        <button
          onClick={() => setActiveTab('patterns')}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'patterns' ? 'bg-blue-600 text-white' : 'bg-gray-200'
          }`}
        >
          Alert Patterns
        </button>
        <button
          onClick={() => setActiveTab('filters')}
          className={`px-4 py-2 rounded-lg font-medium ${
            activeTab === 'filters' ? 'bg-blue-600 text-white' : 'bg-gray-200'
          }`}
        >
          Filters
        </button>
      </div>

      {/* Communities Tab */}
      {activeTab === 'communities' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-gray-600">Manage multiple Discord communities</p>
            <Button onClick={addCommunity}>Add Community</Button>
          </div>
          
          {communities.map((community) => (
            <Card key={community.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={community.enabled}
                      onCheckedChange={(v) => updateCommunity(community.id, 'enabled', v)}
                    />
                    <CardTitle>{community.name}</CardTitle>
                  </div>
                  <Button variant="destructive" size="sm" onClick={() => removeCommunity(community.id)}>
                    Remove
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Community Name</Label>
                    <Input
                      value={community.name}
                      onChange={(e) => updateCommunity(community.id, 'name', e.target.value)}
                    />
                  </div>
                  <div>
                    <Label>Channel ID</Label>
                    <Input
                      value={community.channelId}
                      onChange={(e) => updateCommunity(community.id, 'channelId', e.target.value)}
                      placeholder="123456789"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label>Preset</Label>
                    <Select
                      value={community.preset}
                      onValueChange={(v) => updateCommunity(community.id, 'preset', v)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {presets.map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label>Bot Token</Label>
                    <Input
                      type="password"
                      placeholder="Discord bot token"
                    />
                  </div>
                  
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={community.autoTrade}
                        onCheckedChange={(v) => updateCommunity(community.id, 'autoTrade', v)}
                      />
                      <Label>Auto Trade</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={community.simulation}
                        onCheckedChange={(v) => updateCommunity(community.id, 'simulation', v)}
                      />
                      <Label>Simulation</Label>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Patterns Tab */}
      {activeTab === 'patterns' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Alert Patterns</CardTitle>
              <CardDescription>Customize what keywords trigger alerts</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Buy Keywords */}
              <div>
                <Label>Buy Keywords (comma-separated)</Label>
                <Input
                  value={patterns.buyKeywords}
                  onChange={(e) => setPatterns({...patterns, buyKeywords: e.target.value})}
                  placeholder="BUY,ENTRY,LONG,BTO"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Keywords that trigger a BUY alert
                </p>
              </div>
              
              {/* Sell Keywords */}
              <div>
                <Label>Sell Keywords (comma-separated)</Label>
                <Input
                  value={patterns.sellKeywords}
                  onChange={(e) => setPatterns({...patterns, sellKeywords: e.target.value})}
                  placeholder="SELL,EXIT,CLOSE,STC"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Keywords that trigger a SELL alert
                </p>
              </div>
              
              {/* Average Down Keywords */}
              <div>
                <Label>Average Down Keywords</Label>
                <Input
                  value={patterns.avgDownKeywords}
                  onChange={(e) => setPatterns({...patterns, avgDownKeywords: e.target.value})}
                  placeholder="AVERAGE DOWN,AVG DOWN"
                />
              </div>
              
              {/* Ignore Keywords */}
              <div>
                <Label>Ignore Keywords</Label>
                <Input
                  value={patterns.ignoreKeywords}
                  onChange={(e) => setPatterns({...patterns, ignoreKeywords: e.target.value})}
                  placeholder="WATCHLIST,PAPER"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Messages with these keywords will be ignored
                </p>
              </div>
              
              <hr />
              
              {/* Requirements */}
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <Switch
                    checked={patterns.requireTicker}
                    onCheckedChange={(v) => setPatterns({...patterns, requireTicker: v})}
                  />
                  <Label>Require $Ticker</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={patterns.requireExpiration}
                    onCheckedChange={(v) => setPatterns({...patterns, requireExpiration: v})}
                  />
                  <Label>Require Expiration</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={patterns.requirePrice}
                    onCheckedChange={(v) => setPatterns({...patterns, requirePrice: v})}
                  />
                  <Label>Require Price</Label>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Pattern Presets */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Presets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-2">
                {presets.slice(0, -1).map(preset => (
                  <Button
                    key={preset.id}
                    variant="outline"
                    onClick={() => {
                      // Would load preset patterns here
                      alert(`Loaded preset: ${preset.name}`);
                    }}
                  >
                    {preset.name}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters Tab */}
      {activeTab === 'filters' && (
        <Card>
          <CardHeader>
            <CardTitle>Message Filters</CardTitle>
            <CardDescription>Filter which messages are processed</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Listen to Users (comma-separated IDs)</Label>
                <Input
                  value={filters.listenToUsers}
                  onChange={(e) => setFilters({...filters, listenToUsers: e.target.value})}
                  placeholder="user123, user456"
                />
                <p className="text-xs text-gray-500 mt-1">Empty = all users</p>
              </div>
              <div>
                <Label>Ignore Users</Label>
                <Input
                  value={filters.ignoreUsers}
                  onChange={(e) => setFilters({...filters, ignoreUsers: e.target.value})}
                  placeholder="baduser"
                />
              </div>
            </div>
            
            <div>
              <Label>Listen to Channels (comma-separated IDs)</Label>
              <Input
                value={filters.listenToChannels}
                onChange={(e) => setFilters({...filters, listenToChannels: e.target.value})}
                placeholder="123456, 789012"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Min Price ($)</Label>
                <Input
                  type="number"
                  value={filters.minPrice}
                  onChange={(e) => setFilters({...filters, minPrice: Number(e.target.value)})}
                />
              </div>
              <div>
                <Label>Max Price ($)</Label>
                <Input
                  type="number"
                  value={filters.maxPrice}
                  onChange={(e) => setFilters({...filters, maxPrice: Number(e.target.value)})}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mt-6 flex justify-end gap-2">
        <Button variant="outline">Reset</Button>
        <Button>Save Discord Settings</Button>
      </div>
    </div>
  );
}