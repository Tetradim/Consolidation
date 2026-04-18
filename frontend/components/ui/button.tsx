import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';

export function Button({ children, onPress, variant = 'primary', style }: any) {
  return (
    <TouchableOpacity style={[styles.button, variant === 'outline' && styles.outline, style]} onPress={onPress}>
      <Text style={styles.text}>{children}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: { backgroundColor: '#007AFF', padding: 12, borderRadius: 6, alignItems: 'center' },
  outline: { backgroundColor: 'transparent', borderWidth: 1, borderColor: '#007AFF' },
  text: { color: '#fff', fontWeight: '600' },
});
