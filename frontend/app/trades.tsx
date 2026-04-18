import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  RefreshControl, ActivityIndicator, Modal, TextInput, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../utils/api';
import { BACKEND_URL } from '../constants/config';
import { BROKER_COLORS, BROKER_NAMES } from '../constants/brokers';
import { validatePrice, formatDate, formatPnL, getPnLColor } from '../utils/format';

interface Trade {
  id: string; ticker: string; strike: number; option_type: string;
  expiration: string; entry_price: number; exit_price: number | null;
  current_price: number | null; quantity: number; status: string;
  executed_at: string | null; closed_at: string | null; broker: string;
  order_id: string | null; error_message: string | null; simulated: boolean;
  realized_pnl: number | null; unrealized_pnl: number | null;
}
interface PortfolioSummary {
  total_pnl: number; total_realized_pnl: number; total_unrealized_pnl: number;
  win_rate: number; open_positions: number; closed_positions: number;
  winning_trades: number; losing_trades: number;
}

type Filter = 'all' | 'open' | 'closed';

function statusInfo(status: string, simulated: boolean) {
  if (simulated && status !== 'closed') return { color: '#a78bfa', bg: '#2d1f5e', label: 'SIM' };
  switch (status) {
    case 'executed': return { color: '#4ade80', bg: '#14532d', label: 'OPEN' };
    case 'closed':   return { color: '#38bdf8', bg: '#0c2740', label: 'CLOSED' };
    case 'failed':   return { color: '#f87171', bg: '#450a0a', label: 'FAILED' };
    case 'pending':  return { color: '#fb923c', bg: '#422006', label: 'PEND' };
    default:         return { color: '#64748b', bg: '#1e2d3d', label: status.toUpperCase() };
  }
}

export default function TradesScreen() {
  const [trades, setTrades]       = useState<Trade[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter]       = useState<Filter>('all');
  const [selected, setSelected]   = useState<Trade | null>(null);
  const [showClose, setShowClose] = useState(false);
  const [showUpdate, setShowUpdate] = useState(false);
  const [exitPrice, setExitPrice] = useState('');
  const [currPrice, setCurrPrice] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchTrades = useCallback(async () => {
    try {
      const [tr, pr] = await Promise.all([
        api.get(`${BACKEND_URL}/api/trades?limit=200`),
        api.get(`${BACKEND_URL}/api/portfolio`),
      ]);
      setTrades(tr.data);
      setPortfolio(pr.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useEffect(() => { fetchTrades(); }, [fetchTrades]);
  const onRefresh = useCallback(() => { setRefreshing(true); fetchTrades(); }, [fetchTrades]);

  const filtered = trades.filter(t =>
    filter === 'all'    ? true :
    filter === 'open'   ? (t.status !== 'closed' && t.status !== 'failed') :
    (t.status === 'closed' || t.status === 'failed')
  );

  const closeTrade = async () => {
    if (!selected) return;
    const r = validatePrice(exitPrice);
    if (r.error) { Alert.alert('Invalid Price', r.error); return; }
    Alert.alert('Confirm Close', `Close $${selected.ticker} at $${r.value?.toFixed(2)}? Cannot be undone.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Close Trade', style: 'destructive', onPress: async () => {
        setSubmitting(true);
        try {
          await api.post(`${BACKEND_URL}/api/trades/${selected.id}/close`, { exit_price: r.value });
          setShowClose(false); setSelected(null); setExitPrice(''); fetchTrades();
        } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed to close trade'); }
        finally { setSubmitting(false); }
      }}
    ]);
  };

  const updatePrice = async () => {
    if (!selected) return;
    const r = validatePrice(currPrice, { min: 0.01 });
    if (r.error) { Alert.alert('Invalid Price', r.error); return; }
    setSubmitting(true);
    try {
      await api.put(`${BACKEND_URL}/api/trades/${selected.id}/price`, { current_price: r.value });
      setShowUpdate(false); setSelected(null); setCurrPrice(''); fetchTrades();
    } catch (e: any) { Alert.alert('Error', e.response?.data?.detail || 'Failed to update'); }
    finally { setSubmitting(false); }
  };

  const renderItem = ({ item: t }: { item: Trade }) => {
    const si = statusInfo(t.status, t.simulated);
    const bColor = BROKER_COLORS[t.broker] || '#64748b';
    const bName  = BROKER_NAMES[t.broker] || t.broker;
    const pnl    = t.realized_pnl !== null ? t.realized_pnl : t.unrealized_pnl;
    const isOpen = t.status !== 'closed' && t.status !== 'failed';

    return (
      <View style={s.card}>
        {/* Top row */}
        <View style={s.cardTop}>
          <View style={s.tickerRow}>
            <Text style={s.ticker}>${t.ticker}</Text>
            <View style={[s.typePill, { backgroundColor: t.option_type === 'CALL' ? '#14532d' : '#450a0a' }]}>
              <Text style={[s.typeText, { color: t.option_type === 'CALL' ? '#4ade80' : '#f87171' }]}>{t.option_type}</Text>
            </View>
          </View>
          <View style={s.badges}>
            <View style={[s.badge, { backgroundColor: bColor + '22', borderColor: bColor + '44', borderWidth: 1 }]}>
              <Text style={[s.badgeText, { color: bColor }]}>{bName}</Text>
            </View>
            <View style={[s.badge, { backgroundColor: si.bg }]}>
              <Text style={[s.badgeText, { color: si.color }]}>{si.label}</Text>
            </View>
          </View>
        </View>

        {/* Stats grid */}
        <View style={s.grid}>
          {[
            { label: 'STRIKE', value: `$${t.strike}` },
            { label: 'ENTRY',  value: `$${t.entry_price.toFixed(2)}` },
            { label: t.exit_price ? 'EXIT' : 'CURRENT', value: `$${(t.exit_price ?? t.current_price ?? t.entry_price).toFixed(2)}` },
            { label: 'QTY',    value: String(t.quantity) },
          ].map(({ label, value }) => (
            <View key={label} style={s.gridCell}>
              <Text style={s.gridLabel}>{label}</Text>
              <Text style={s.gridValue}>{value}</Text>
            </View>
          ))}
        </View>

        {/* P&L */}
        {pnl !== null && (
          <View style={[s.pnlRow, { backgroundColor: pnl >= 0 ? '#14280a' : '#2d1515' }]}>
            <Ionicons name={pnl >= 0 ? 'trending-up' : 'trending-down'} size={16} color={getPnLColor(pnl)} />
            <Text style={[s.pnlText, { color: getPnLColor(pnl) }]}>
              {t.realized_pnl !== null ? 'Realized' : 'Unrealized'}: {formatPnL(pnl)}
            </Text>
          </View>
        )}

        {/* Error */}
        {t.error_message && (
          <View style={s.errorRow}>
            <Ionicons name="alert-circle-outline" size={13} color="#f87171" />
            <Text style={s.errorText} numberOfLines={2}>{t.error_message}</Text>
          </View>
        )}

        {/* Footer */}
        <View style={s.cardFooter}>
          <Text style={s.footerTime}>{formatDate(t.executed_at)}</Text>
          {isOpen && (
            <View style={s.actions}>
              <TouchableOpacity style={s.actionBtn} onPress={() => { setSelected(t); setCurrPrice(t.current_price?.toString() || t.entry_price.toString()); setShowUpdate(true); }}>
                <Text style={s.actionBtnText}>Update</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[s.actionBtn, s.actionBtnClose]} onPress={() => { setSelected(t); setExitPrice(t.current_price?.toString() || t.entry_price.toString()); setShowClose(true); }}>
                <Text style={[s.actionBtnText, { color: '#f87171' }]}>Close</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={s.container}>
      {/* Header */}
      <View style={s.header}>
        <View>
          <Text style={s.eyebrow}>TRADE HISTORY</Text>
          <Text style={s.title}>Trades</Text>
        </View>
        {portfolio && (
          <View style={s.headerPnl}>
            <Text style={[s.headerPnlNum, { color: getPnLColor(portfolio.total_pnl) }]}>
              {formatPnL(portfolio.total_pnl)}
            </Text>
            <Text style={s.headerPnlLabel}>{portfolio.win_rate.toFixed(0)}% win rate</Text>
          </View>
        )}
      </View>

      {/* Stats strip */}
      {portfolio && (
        <View style={s.strip}>
          {[
            { label: 'Open',    value: String(portfolio.open_positions) },
            { label: 'Closed',  value: String(portfolio.closed_positions) },
            { label: 'Wins',    value: String(portfolio.winning_trades),  color: '#22c55e' },
            { label: 'Losses',  value: String(portfolio.losing_trades),   color: '#ef4444' },
            { label: 'Realized', value: formatPnL(portfolio.total_realized_pnl), color: getPnLColor(portfolio.total_realized_pnl) },
          ].map(({ label, value, color }) => (
            <View key={label} style={s.stripCell}>
              <Text style={[s.stripValue, color ? { color } : {}]}>{value}</Text>
              <Text style={s.stripLabel}>{label}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Filter */}
      <View style={s.filterBar}>
        {(['all', 'open', 'closed'] as Filter[]).map(f => (
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
              <Ionicons name="receipt-outline" size={48} color="#1e2d3d" />
              <Text style={s.emptyTitle}>No trades</Text>
            </View>
          }
        />
      )}

      {/* Close Modal */}
      <Modal visible={showClose} transparent animationType="fade">
        <View style={s.overlay}>
          <View style={s.modal}>
            <Text style={s.modalTitle}>Close Trade</Text>
            <Text style={s.modalSub}>{selected?.ticker} {selected?.strike} {selected?.option_type}</Text>
            <Text style={s.modalLabel}>Exit Price</Text>
            <TextInput
              style={s.modalInput} value={exitPrice} onChangeText={setExitPrice}
              keyboardType="decimal-pad" placeholder="0.00" placeholderTextColor="#334155"
            />
            <View style={s.modalBtns}>
              <TouchableOpacity style={s.modalCancel} onPress={() => setShowClose(false)}>
                <Text style={s.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={s.modalConfirm} onPress={closeTrade} disabled={submitting}>
                {submitting ? <ActivityIndicator size="small" color="#fff" /> : <Text style={s.modalConfirmText}>Close Trade</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Update Price Modal */}
      <Modal visible={showUpdate} transparent animationType="fade">
        <View style={s.overlay}>
          <View style={s.modal}>
            <Text style={s.modalTitle}>Update Price</Text>
            <Text style={s.modalSub}>{selected?.ticker} {selected?.strike} {selected?.option_type}</Text>
            <Text style={s.modalLabel}>Current Price</Text>
            <TextInput
              style={s.modalInput} value={currPrice} onChangeText={setCurrPrice}
              keyboardType="decimal-pad" placeholder="0.00" placeholderTextColor="#334155"
            />
            <View style={s.modalBtns}>
              <TouchableOpacity style={s.modalCancel} onPress={() => setShowUpdate(false)}>
                <Text style={s.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[s.modalConfirm, { backgroundColor: '#0ea5e9' }]} onPress={updatePrice} disabled={submitting}>
                {submitting ? <ActivityIndicator size="small" color="#fff" /> : <Text style={s.modalConfirmText}>Update</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container:  { flex: 1, backgroundColor: '#080f1a' },
  centered:   { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header:     { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', paddingHorizontal: 20, paddingTop: 16, paddingBottom: 12 },
  eyebrow:    { fontSize: 10, color: '#0ea5e9', fontWeight: '700', letterSpacing: 2, marginBottom: 2 },
  title:      { fontSize: 26, fontWeight: '800', color: '#e2e8f0' },
  headerPnl:  { alignItems: 'flex-end' },
  headerPnlNum: { fontSize: 20, fontWeight: '800' },
  headerPnlLabel: { fontSize: 11, color: '#475569', marginTop: 1 },

  strip:      { flexDirection: 'row', marginHorizontal: 16, backgroundColor: '#0d1826', borderRadius: 12, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: '#1e2d3d' },
  stripCell:  { flex: 1, alignItems: 'center' },
  stripValue: { fontSize: 13, fontWeight: '700', color: '#e2e8f0' },
  stripLabel: { fontSize: 9, color: '#475569', marginTop: 2, fontWeight: '600', letterSpacing: 0.5 },

  filterBar:  { flexDirection: 'row', paddingHorizontal: 16, gap: 8, marginBottom: 10 },
  filterBtn:  { paddingHorizontal: 16, paddingVertical: 7, borderRadius: 8, backgroundColor: '#0d1826', borderWidth: 1, borderColor: '#1e2d3d' },
  filterBtnActive: { backgroundColor: '#0c2740', borderColor: '#0ea5e9' },
  filterText: { fontSize: 13, color: '#475569', fontWeight: '600' },
  filterTextActive: { color: '#0ea5e9' },

  list:       { paddingHorizontal: 16, paddingBottom: 16 },
  card:       { backgroundColor: '#0d1826', borderRadius: 12, padding: 14, marginBottom: 8, borderWidth: 1, borderColor: '#1e2d3d' },
  cardTop:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  tickerRow:  { flexDirection: 'row', alignItems: 'center', gap: 8 },
  ticker:     { fontSize: 18, fontWeight: '800', color: '#e2e8f0' },
  typePill:   { paddingHorizontal: 7, paddingVertical: 3, borderRadius: 5 },
  typeText:   { fontSize: 11, fontWeight: '700' },
  badges:     { flexDirection: 'row', gap: 6 },
  badge:      { paddingHorizontal: 7, paddingVertical: 3, borderRadius: 5 },
  badgeText:  { fontSize: 10, fontWeight: '700' },

  grid:       { flexDirection: 'row', gap: 4, marginBottom: 10 },
  gridCell:   { flex: 1, backgroundColor: '#111c2a', borderRadius: 7, padding: 8, alignItems: 'center' },
  gridLabel:  { fontSize: 9, color: '#334155', fontWeight: '700', letterSpacing: 1, marginBottom: 3 },
  gridValue:  { fontSize: 13, fontWeight: '700', color: '#e2e8f0' },

  pnlRow:     { flexDirection: 'row', alignItems: 'center', gap: 7, padding: 8, borderRadius: 7, marginBottom: 8 },
  pnlText:    { fontSize: 13, fontWeight: '700' },
  errorRow:   { flexDirection: 'row', alignItems: 'flex-start', gap: 6, backgroundColor: '#2d1515', borderRadius: 6, padding: 8, marginBottom: 8 },
  errorText:  { flex: 1, fontSize: 11, color: '#f87171' },

  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingTop: 8, borderTopWidth: 1, borderTopColor: '#111c2a' },
  footerTime: { fontSize: 10, color: '#334155' },
  actions:    { flexDirection: 'row', gap: 6 },
  actionBtn:  { paddingHorizontal: 12, paddingVertical: 5, borderRadius: 6, backgroundColor: '#1e2d3d' },
  actionBtnClose: { backgroundColor: '#2d1515' },
  actionBtnText: { fontSize: 12, color: '#94a3b8', fontWeight: '600' },

  empty:      { alignItems: 'center', paddingVertical: 64, gap: 10 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: '#1e2d3d' },

  overlay:    { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', alignItems: 'center', justifyContent: 'center', padding: 24 },
  modal:      { backgroundColor: '#0d1826', borderRadius: 16, padding: 24, width: '100%', maxWidth: 380, borderWidth: 1, borderColor: '#1e2d3d' },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#e2e8f0', marginBottom: 4 },
  modalSub:   { fontSize: 13, color: '#475569', marginBottom: 20 },
  modalLabel: { fontSize: 12, color: '#64748b', fontWeight: '600', marginBottom: 8 },
  modalInput: { backgroundColor: '#111c2a', borderRadius: 9, padding: 14, color: '#e2e8f0', fontSize: 18, fontWeight: '700', borderWidth: 1, borderColor: '#1e2d3d', marginBottom: 20 },
  modalBtns:  { flexDirection: 'row', gap: 10 },
  modalCancel:  { flex: 1, padding: 14, borderRadius: 9, backgroundColor: '#1e2d3d', alignItems: 'center' },
  modalCancelText: { color: '#64748b', fontWeight: '700' },
  modalConfirm:  { flex: 1, padding: 14, borderRadius: 9, backgroundColor: '#7f1d1d', alignItems: 'center' },
  modalConfirmText: { color: '#fff', fontWeight: '700' },
});
