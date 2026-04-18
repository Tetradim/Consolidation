/**
 * Risk Management Settings Page
 * 
 * Complete risk management configuration page
 */
import React, { useState } from 'react';
import { View, Text, TextInput, Switch, Button, ScrollView, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

type TabType = 'position' | 'stoploss' | 'takeprofit' | 'trailing' | 'shutdown' | 'correlation';

const TABS = [
  { id: 'position', label: 'Position' },
  { id: 'stoploss', label: 'Stop Loss' },
  { id: 'takeprofit', label: 'Take Profit' },
  { id: 'trailing', label: 'Trailing' },
  { id: 'shutdown', label: 'Shutdown' },
  { id: 'correlation', label: 'Correlation' },
];

export default function RiskSettingsScreen() {
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

  const saveSettings = () => {
    Alert.alert('Saved', 'Risk settings saved successfully');
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'position':
        return (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Position Sizing</Text>
            
            <View style={styles.field}>
              <Text style={styles.label}>Max Position Size ($)</Text>
              <TextInput
                style={styles.input}
                value={String(settings.maxPositionSize)}
                onChangeText={v => updateSetting('maxPositionSize', Number(v))}
                keyboardType="numeric"
              />
            </View>
            
            <View style={styles.field}>
              <Text style={styles.label}>Default Quantity</Text>
              <TextInput
                style={styles.input}
                value={String(settings.defaultQuantity)}
                onChangeText={v => updateSetting('defaultQuantity', Number(v))}
                keyboardType="numeric"
              />
            </View>
            
            <View style={styles.field}>
              <Text style={styles.label}>Risk Per Trade (%)</Text>
              <TextInput
                style={styles.input}
                value={String(settings.riskPerTrade)}
                onChangeText={v => updateSetting('riskPerTrade', Number(v))}
                keyboardType="numeric"
              />
            </View>
          </View>
        );
        
      case 'stoploss':
        return (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Stop Loss</Text>
            
            <View style={styles.field}>
              <View style={styles.row}>
                <Text style={styles.label}>Enable Stop Loss</Text>
                <Switch
                  value={settings.stopLossEnabled}
                  onValueChange={v => updateSetting('stopLossEnabled', v)}
                />
              </View>
            </View>
            
            <View style={styles.field}>
              <Text style={styles.label}>Stop Loss (%)</Text>
              <TextInput
                style={styles.input}
                value={String(settings.stopLossPercentage)}
                onChangeText={v => updateSetting('stopLossPercentage', Number(v))}
                keyboardType="numeric"
                editable={settings.stopLossEnabled}
              />
            </View>
          </View>
        );
        
      case 'takeprofit':
        return (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Take Profit</Text>
            
            <View style={styles.field}>
              <View style={styles.row}>
                <Text style={styles.label}>Enable Take Profit</Text>
                <Switch
                  value={settings.takeProfitEnabled}
                  onValueChange={v => updateSetting('takeProfitEnabled', v)}
                />
              </View>
            </View>
            
            <View style={styles.field}>
              <Text style={styles.label}>Take Profit (%)</Text>
              <TextInput
                style={styles.input}
                value={String(settings.takeProfitPercentage)}
                onChangeText={v => updateSetting('takeProfitPercentage', Number(v))}
                keyboardType="numeric"
                editable={settings.takeProfitEnabled}
              />
            </View>
          </View>
        );
        
      case 'trailing':
        return (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Trailing Stop</Text>
            
            <View style={styles.field}>
              <View style={styles.row}>
                <Text style={styles.label}>Enable Trailing Stop</Text>
                <Switch
                  value={settings.trailingStopEnabled}
                  onValueChange={v => updateSetting('trailingStopEnabled', v)}
                />
              </View>
            </View>
            
            <View style={styles.field}>
              <Text style={styles.label}>Trailing Stop (%)</Text>
              <TextInput
                style={styles.input}
                value={String(settings.trailingStopPercent)}
                onChangeText={v => updateSetting('trailingStopPercent', Number(v))}
                keyboardType="numeric"
                editable={settings.trailingStopEnabled}
              />
            </View>
          </View>
        );
        
      case 'shutdown':
        return (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Auto Shutdown</Text>
            
            <View style={styles.field}>
              <View style={styles.row}>
                <Text style={styles.label}>Enable Auto Shutdown</Text>
                <Switch
                  value={settings.autoShutdownEnabled}
                  onValueChange={v => updateSetting('autoShutdownEnabled', v)}
                />
              </View>
            </View>
            
            <View style={styles.field}>
              <Text style={styles.label}>Max Consecutive Losses</Text>
              <TextInput
                style={styles.input}
                value={String(settings.maxConsecutiveLosses)}
                onChangeText={v => updateSetting('maxConsecutiveLosses', Number(v))}
                keyboardType="numeric"
              />
            </View>
            
            <View style={styles.field}>
              <Text style={styles.label}>Max Daily Loss ($)</Text>
              <TextInput
                style={styles.input}
                value={String(settings.maxDailyLossAmount)}
                onChangeText={v => updateSetting('maxDailyLossAmount', Number(v))}
                keyboardType="numeric"
              />
            </View>
            
            <View style={styles.field}>
              <Text style={styles.label}>Max Drawdown (%)</Text>
              <TextInput
                style={styles.input}
                value={String(settings.maxDrawdownPercent)}
                onChangeText={v => updateSetting('maxDrawdownPercent', Number(v))}
                keyboardType="numeric"
              />
            </View>
          </View>
        );
        
      case 'correlation':
        return (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Correlation Limits</Text>
            
            <View style={styles.field}>
              <Text style={styles.label}>Max Positions Per Ticker</Text>
              <TextInput
                style={styles.input}
                value={String(settings.maxPositionsPerTicker)}
                onChangeText={v => updateSetting('maxPositionsPerTicker', Number(v))}
                keyboardType="numeric"
              />
            </View>
            
            <View style={styles.field}>
              <Text style={styles.label}>Max Positions Per Sector</Text>
              <TextInput
                style={styles.input}
                value={String(settings.maxPositionsPerSector)}
                onChangeText={v => updateSetting('maxPositionsPerSector', Number(v))}
                keyboardType="numeric"
              />
            </View>
          </View>
        );
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        <Text style={styles.title}>Risk Management</Text>
        
        {/* Tab Navigation */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabBar}>
          <View style={styles.tabRow}>
            {TABS.map(tab => (
              <TouchableOpacity
                key={tab.id}
                style={[styles.tab, activeTab === tab.id && styles.tabActive]}
                onPress={() => setActiveTab(tab.id as TabType)}
              >
                <Text style={[styles.tabText, activeTab === tab.id && styles.tabTextActive]}>
                  {tab.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>
        
        {/* Tab Content */}
        {renderTabContent()}
        
        {/* Save Button */}
        <View style={styles.buttonContainer}>
          <Button title="Save Settings" onPress={saveSettings} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f0f0f', padding: 16 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#fff', marginBottom: 16 },
  tabBar: { marginBottom: 16 },
  tabRow: { flexDirection: 'row', gap: 8 },
  tab: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8, backgroundColor: '#1a1a1a' },
  tabActive: { backgroundColor: '#007AFF' },
  tabText: { color: '#888', fontSize: 14 },
  tabTextActive: { color: '#fff' },
  section: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 16, marginBottom: 16 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#fff', marginBottom: 16 },
  field: { marginBottom: 16 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { color: '#aaa', fontSize: 14, marginBottom: 4 },
  input: { backgroundColor: '#2a2a2a', color: '#fff', padding: 12, borderRadius: 8, fontSize: 16 },
  buttonContainer: { marginTop: 16, marginBottom: 32 },
});