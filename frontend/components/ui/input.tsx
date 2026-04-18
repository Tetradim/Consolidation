import React from 'react';
import { TextInput, StyleSheet } from 'react-native';

export function Input(props: any) {
  return <TextInput style={styles.input} placeholderTextColor="#666" {...props} />;
}

const styles = StyleSheet.create({
  input: { backgroundColor: '#2a2a2a', color: '#fff', padding: 12, borderRadius: 6, fontSize: 16 },
});
