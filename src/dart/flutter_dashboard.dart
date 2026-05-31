// flutter_dashboard.dart - Flutter dashboard for SDACS drone monitoring
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class DroneState {
  final String id;
  final double latitude;
  final double longitude;
  final double altitude;
  final int battery;
  final String status;

  DroneState({required this.id, required this.latitude, required this.longitude,
              required this.altitude, required this.battery, required this.status});

  factory DroneState.fromJson(Map<String, dynamic> json) => DroneState(
    id: json['id'], latitude: json['latitude'], longitude: json['longitude'],
    altitude: json['altitude'], battery: json['battery'], status: json['status'],
  );
}

class DashboardViewModel extends ChangeNotifier {
  List<DroneState> drones = [];
  bool isLoading = false;
  final String apiBase;

  DashboardViewModel(this.apiBase);

  Future<void> fetchSnapshot() async {
    isLoading = true;
    notifyListeners();
    try {
      final response = await http.get(Uri.parse('$apiBase/api/v1/snapshot'));
      if (response.statusCode == 200) {
        final List data = json.decode(response.body);
        drones = data.map((d) => DroneState.fromJson(d)).toList();
      }
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }
}
