import React from 'react';
import { View, Text } from 'react-native';

export function Slider({ value, minimumValue, maximumValue, onValueChange }: any) {
  return (
    <View>
      <Text>Slider: {value}</Text>
    </View>
  );
}
