import React from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, Modal, KeyboardAvoidingView, Platform } from 'react-native';

interface CreateProfileModalProps {
  visible: boolean;
  profileName: string;
  profileDescription: string;
  onNameChange: (name: string) => void;
  onDescriptionChange: (description: string) => void;
  onCreate: () => void;
  onCancel: () => void;
}

export const CreateProfileModal: React.FC<CreateProfileModalProps> = ({
  visible,
  profileName,
  profileDescription,
  onNameChange,
  onDescriptionChange,
  onCreate,
  onCancel,
}) => {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onCancel}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.modalOverlay}
      >
        <View style={styles.modal} testID="create-profile-modal">
          <Text style={styles.modalTitle}>Create New Profile</Text>

          <Text style={styles.inputLabel}>Profile Name</Text>
          <TextInput
            style={styles.input}
            value={profileName}
            onChangeText={onNameChange}
            placeholder="e.g., Alpaca Bracket, Robinhood Alerts"
            placeholderTextColor="#64748b"
            autoCorrect={false}
            maxLength={50}
            testID="profile-name-input"
          />

          <Text style={styles.inputLabel}>Description (optional)</Text>
          <TextInput
            style={styles.input}
            value={profileDescription}
            onChangeText={onDescriptionChange}
            placeholder="Optional description"
            placeholderTextColor="#64748b"
            autoCorrect={false}
            maxLength={200}
            testID="profile-description-input"
          />

          <View style={styles.modalButtons}>
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={onCancel}
              testID="cancel-create-profile"
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.createButton, !profileName.trim() && styles.createButtonDisabled]}
              onPress={onCreate}
              disabled={!profileName.trim()}
              testID="confirm-create-profile"
            >
              <Text style={styles.createButtonText}>Create</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modal: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 20,
    width: '100%',
    maxWidth: 400,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 13,
    color: '#94a3b8',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#0f172a',
    borderRadius: 8,
    padding: 12,
    color: '#fff',
    fontSize: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 10,
  },
  cancelButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 6,
  },
  cancelButtonText: {
    color: '#94a3b8',
    fontWeight: '600',
  },
  createButton: {
    backgroundColor: '#3b82f6',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 6,
  },
  createButtonDisabled: {
    opacity: 0.5,
  },
  createButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
});
