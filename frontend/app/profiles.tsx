import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '../utils/api';
import { ProfileCard, CreateProfileModal } from '../components/profiles';

import { BACKEND_URL } from '../constants/config';
import type { BrokerSettingsData, Broker, Profile } from '../types/profiles';

export default function ProfilesScreen() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [brokers, setBrokers] = useState<Broker[]>([]);
  const [allBrokerSettings, setAllBrokerSettings] = useState<Record<string, Record<string, BrokerSettingsData>>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newProfileName, setNewProfileName] = useState('');
  const [newProfileDescription, setNewProfileDescription] = useState('');
  const [expandedProfile, setExpandedProfile] = useState<string | null>(null);
  const [expandedBroker, setExpandedBroker] = useState<string | null>(null);
  // Loading guards to prevent double-tap race conditions (C12)
  const [activatingId, setActivatingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [profilesRes, brokersRes] = await Promise.all([
        api.get(`${BACKEND_URL}/api/profiles`),
        api.get(`${BACKEND_URL}/api/brokers`),
      ]);
      setProfiles(profilesRes.data);
      setBrokers(brokersRes.data);

      // Fetch all profile broker-settings in parallel (fixes N+1, C11)
      const profileList: Profile[] = profilesRes.data;
      const settingsResults = await Promise.all(
        profileList.map((p) =>
          api
            .get(`${BACKEND_URL}/api/profiles/${p.id}/all-broker-settings`)
            .then((r) => ({ id: p.id, data: r.data }))
            .catch(() => ({ id: p.id, data: {} }))
        )
      );
      const settingsMap: Record<string, Record<string, BrokerSettingsData>> = {};
      for (const { id, data } of settingsResults) {
        settingsMap[id] = data;
      }
      setAllBrokerSettings(settingsMap);
    } catch (error) {
      console.error('Error fetching data:', error);
      Alert.alert('Error', 'Failed to load profiles. Pull to refresh.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const createProfile = async () => {
    if (!newProfileName.trim()) return;
    try {
      await api.post(`${BACKEND_URL}/api/profiles`, {
        name: newProfileName.trim(),
        description: newProfileDescription.trim(),
      });
      setNewProfileName('');
      setNewProfileDescription('');
      setShowCreateModal(false);
      fetchData();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to create profile');
    }
  };

  const activateProfile = async (profileId: string) => {
    if (activatingId) return; // guard double-tap
    setActivatingId(profileId);
    try {
      await api.post(`${BACKEND_URL}/api/profiles/${profileId}/activate`);
      fetchData();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to activate profile');
    } finally {
      setActivatingId(null);
    }
  };

  const deleteProfile = async (profileId: string) => {
    if (deletingId) return; // guard double-tap
    setDeletingId(profileId);
    try {
      await api.delete(`${BACKEND_URL}/api/profiles/${profileId}`);
      fetchData();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to delete profile');
    } finally {
      setDeletingId(null);
    }
  };

  const toggleBrokerSetting = async (profileId: string, brokerId: string, settingName: string) => {
    try {
      const res = await api.post(
        `${BACKEND_URL}/api/profiles/${profileId}/brokers/${brokerId}/settings/toggle/${settingName}`
      );
      setAllBrokerSettings(prev => ({
        ...prev,
        [profileId]: {
          ...prev[profileId],
          [brokerId]: res.data.broker_settings
        }
      }));
    } catch (error) {
      Alert.alert('Error', 'Failed to update broker setting.');
    }
  };

  const updateBrokerSetting = async (profileId: string, brokerId: string, settingName: string, value: number) => {
    try {
      const res = await api.put(
        `${BACKEND_URL}/api/profiles/${profileId}/brokers/${brokerId}/settings`,
        { [settingName]: value }
      );
      setAllBrokerSettings(prev => ({
        ...prev,
        [profileId]: {
          ...prev[profileId],
          [brokerId]: res.data
        }
      }));
    } catch (error) {
      Alert.alert('Error', 'Failed to update broker setting value.');
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#3b82f6" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton} testID="back-button">
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Profiles</Text>
        <TouchableOpacity onPress={() => setShowCreateModal(true)} style={styles.addButton} testID="add-profile-button">
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#3b82f6" />}
      >
        <View style={styles.infoCard}>
          <Ionicons name="information-circle" size={20} color="#3b82f6" />
          <Text style={styles.infoText}>
            Each broker has its own settings. Enable a broker and configure bracket orders, trailing stops, etc. independently.
          </Text>
        </View>

        {profiles.map((profile) => (
          <ProfileCard
            key={profile.id}
            profile={profile}
            brokers={brokers}
            brokerSettings={allBrokerSettings[profile.id] || {}}
            isExpanded={expandedProfile === profile.id}
            expandedBrokerId={expandedBroker}
            onProfileExpand={() => {
              setExpandedProfile(expandedProfile === profile.id ? null : profile.id);
              setExpandedBroker(null);
            }}
            onBrokerExpand={setExpandedBroker}
            onToggleBrokerSetting={toggleBrokerSetting}
            onUpdateBrokerSetting={updateBrokerSetting}
            onActivateProfile={activateProfile}
            onDeleteProfile={deleteProfile}
          />
        ))}
      </ScrollView>

      <CreateProfileModal
        visible={showCreateModal}
        profileName={newProfileName}
        profileDescription={newProfileDescription}
        onNameChange={setNewProfileName}
        onDescriptionChange={setNewProfileDescription}
        onCreate={createProfile}
        onCancel={() => setShowCreateModal(false)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'space-between', 
    paddingHorizontal: 20, 
    paddingVertical: 16, 
    borderBottomWidth: 1, 
    borderBottomColor: '#1e293b' 
  },
  backButton: { padding: 4 },
  headerTitle: { fontSize: 20, fontWeight: '700', color: '#fff' },
  addButton: { padding: 4 },
  content: { flex: 1, padding: 16 },
  infoCard: { 
    flexDirection: 'row', 
    backgroundColor: '#1e3a5f', 
    padding: 12, 
    borderRadius: 8, 
    marginBottom: 16, 
    gap: 10 
  },
  infoText: { flex: 1, color: '#93c5fd', fontSize: 13, lineHeight: 18 },
});
