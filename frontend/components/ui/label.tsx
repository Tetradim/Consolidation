import React from 'react';
import { Text, StyleSheet } from 'react-native';

export function Label({ children, style }: any) {
  return <Text style={[styles.label, style]}>{children}</Text>;
}

const styles = StyleSheet.create({
  label: { color: '#aaa', fontSize: 14, marginBottom: 4 },
});
