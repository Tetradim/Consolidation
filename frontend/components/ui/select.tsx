import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

export function Select({ children, onValueChange, value }: any) {
  return <View>{children}</View>;
}

export function SelectTrigger({ children, style }: any) {
  return <TouchableOpacity style={[styles.trigger, style]}><Text style={styles.text}>{children || 'Select...'}</Text></TouchableOpacity>;
}

export function SelectContent({ children }: any) {
  return <View style={styles.content}>{children}</View>;
}

export function SelectItem({ children, value, onPress }: any) {
  return <TouchableOpacity style={styles.item} onPress={onPress}><Text style={styles.itemText}>{children}</Text></TouchableOpacity>;
}

export function SelectValue({ placeholder }: any) {
  return <Text style={styles.text}>{placeholder}</Text>;
}

const styles = StyleSheet.create({
  trigger: { backgroundColor: '#2a2a2a', padding: 12, borderRadius: 6 },
  text: { color: '#fff' },
  content: { backgroundColor: '#1e1e1e', borderRadius: 6, marginTop: 4 },
  item: { padding: 12 },
  itemText: { color: '#fff' },
});
