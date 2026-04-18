import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList,
  TouchableOpacity, RefreshControl, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../utils/api';
import { BACKEND_URL } from '../constants/config';

interface AlertItem {
  id: string; ticker: string; strike: number; option_type: string;
  expiration: string; entry_price: number; raw_message: string;
  channel_name: string; received_at: string; processed: boolean; trade_executed: boolean;
}

type Filter = 'all' | 'executed' | 'pending';

export default function AlertsScreen() {
  const [alerts, setAlerts]     = useState<AlertItem[]>([]);
  const [loading, setLoading]   = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter]     = useState<Filter>('all');

  const fetchAlerts = useCallback(async () => {
    try {
      const r = await api.get(`${BACKEND_URL}/api/alerts?limit=200`);
      setAlerts(r.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);
  const onRefresh = useCallback(() => { setRefreshing(true); fetchAlerts(); }, [fetchAlerts]);

  const filtered = alerts.filter(a =>
    filter === 'all'      ? true :
    filter === 'executed' ? a.trade_executed :
    !a.trade_executed
  );

  const fmt = (d: string) => new Date(d).toLocaleString();

  const renderItem = ({ item: a }: { item: AlertItem }) => (
    <View style={s.card}>
      <View style={s.cardTop}>
        <View style={s.tickerWrap}>
          <Text style={s.ticker}>${a.ticker}</Text>
          <View style={[s.typePill, { backgroundColor: a.option_type === 'CALL' ? '#14532d' : '#450a0a' }]}>
            <Text style={[s.typeText, { color: a.option_type === 'CALL' ? '#4ade80' : '#f87171' }]}>
              {a.option_type}
            </Text>
          </View>
        </View>
        <View style={[s.statusPill, {
          backgroundColor: a.trade_executed ? '#14532d' : a.processed ? '#422006' : '#1e2d3d'
        }]}>
          <View style={[s.statusDot, {
            backgroundColor: a.trade_executed ? '#22c55e' : a.processed ? '#fb923c' : '#475569'
          }]} />
          <Text style={[s.statusText, {
            color: a.trade_executed ? '#4ade80' : a.processed ? '#fb923c' : '#64748b'
          }]}>
            {a.trade_executed ? 'Executed' : a.processed ? 'Processing' : 'Pending'}
          </Text>
        </View>
      </View>

      <View style={s.grid}>
        <View style={s.gridItem}>
          <Text style={s.gridLabel}>STRIKE</Text>
          <Text style={s.gridValue}>${a.strike}</Text>
        </View>
        <View style={s.gridItem}>
          <Text style={s.gridLabel}>EXPIRY</Text>
          <Text style={s.gridValue}>{a.expiration}</Text>
        </View>
        <View style={s.gridItem}>
          <Text style={s.gridLabel}>ENTRY</Text>
          <Text style={s.gridValue}>${a.entry_price.toFixed(2)}</Text>
        </View>
      </View>

      <View style={s.cardBottom}>
        {a.channel_name ? (
          <View style={s.channelRow}>
            <Ionicons name="chatbubble-outline" size={12} color="#334155" />
            <Text style={s.channelText}>#{a.channel_name}</Text>
          </View>
        ) : <View />}
        <Text style={s.timestamp}>{fmt(a.received_at)}</Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={s.container}>
      {/* Header */}
      <View style={s.header}>
        <View>
          <Text style={s.eyebrow}>DISCORD ALERTS</Text>
          <Text style={s.title}>Alerts</Text>
        </View>
        <View style={s.countBadge}>
          <Text style={s.countText}>{alerts.length}</Text>
        </View>
      </View>

      {/* Filter bar */}
      <View style={s.filterBar}>
        {(['all', 'executed', 'pending'] as Filter[]).map(f => (
          <TouchableOpacity key={f} style={[s.filterBtn, filter === f && s.filterBtnActive]} onPress={() => setFilter(f)}>
            <Text style={[s.filterText, filter === f && s.filterTextActive]}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <View style={s.centered}><ActivityIndicator size="large" color="#0ea5e9" /></View>
      ) : (
        <FlatList
          data={filtered}
          renderItem={renderItem}
          keyExtractor={i => i.id}
          contentContainerStyle={s.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#0ea5e9" />}
          ListEmptyComponent={
            <View style={s.empty}>
              <Ionicons name="notifications-off-outline" size={48} color="#1e2d3d" />
              <Text style={s.emptyTitle}>No alerts</Text>
              <Text style={s.emptySub}>Alerts from Discord will appear here</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container:      { flex: 1, backgroundColor: '#080f1a' },
  centered:       { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header:         { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', paddingHorizontal: 20, paddingTop: 16, paddingBottom: 12 },
  eyebrow:        { fontSize: 10, color: '#0ea5e9', fontWeight: '700', letterSpacing: 2, marginBottom: 2 },
  title:          { fontSize: 26, fontWeight: '800', color: '#e2e8f0' },
  countBadge:     { backgroundColor: '#0d1826', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: '#1e2d3d' },
  countText:      { fontSize: 16, fontWeight: '700', color: '#94a3b8' },

  filterBar:      { flexDirection: 'row', paddingHorizontal: 16, gap: 8, marginBottom: 12 },
  filterBtn:      { paddingHorizontal: 16, paddingVertical: 7, borderRadius: 8, backgroundColor: '#0d1826', borderWidth: 1, borderColor: '#1e2d3d' },
  filterBtnActive:{ backgroundColor: '#0c2740', borderColor: '#0ea5e9' },
  filterText:     { fontSize: 13, color: '#475569', fontWeight: '600' },
  filterTextActive:{ color: '#0ea5e9' },

  list:           { paddingHorizontal: 16, paddingBottom: 16 },

  card:           { backgroundColor: '#0d1826', borderRadius: 12, padding: 14, marginBottom: 8, borderWidth: 1, borderColor: '#1e2d3d' },
  cardTop:        { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  tickerWrap:     { flexDirection: 'row', alignItems: 'center', gap: 8 },
  ticker:         { fontSize: 18, fontWeight: '800', color: '#e2e8f0' },
  typePill:       { paddingHorizontal: 7, paddingVertical: 3, borderRadius: 5 },
  typeText:       { fontSize: 11, fontWeight: '700' },
  statusPill:     { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 9, paddingVertical: 4, borderRadius: 6 },
  statusDot:      { width: 6, height: 6, borderRadius: 3 },
  statusText:     { fontSize: 11, fontWeight: '700' },

  grid:           { flexDirection: 'row', marginBottom: 12, gap: 4 },
  gridItem:       { flex: 1, backgroundColor: '#111c2a', borderRadius: 7, padding: 8, alignItems: 'center' },
  gridLabel:      { fontSize: 9, color: '#334155', fontWeight: '700', letterSpacing: 1, marginBottom: 3 },
  gridValue:      { fontSize: 14, fontWeight: '700', color: '#e2e8f0' },

  cardBottom:     { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  channelRow:     { flexDirection: 'row', alignItems: 'center', gap: 5 },
  channelText:    { fontSize: 11, color: '#334155' },
  timestamp:      { fontSize: 10, color: '#334155' },

  empty:          { alignItems: 'center', paddingVertical: 64, gap: 10 },
  emptyTitle:     { fontSize: 18, fontWeight: '700', color: '#1e2d3d' },
  emptySub:       { fontSize: 13, color: '#1e2d3d' },
});
