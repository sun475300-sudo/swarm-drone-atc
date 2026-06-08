import React from "react";
import HealthBadge from "./HealthBadge.jsx";
import ScenarioList from "./ScenarioList.jsx";
import SnapshotPanel from "./SnapshotPanel.jsx";
import TelemetryFeed from "./TelemetryFeed.jsx";

export default function Dashboard() {
  return (
    <div className="dashboard">
      <HealthBadge />
      <div className="grid">
        <ScenarioList />
        <SnapshotPanel />
        <TelemetryFeed />
      </div>
    </div>
  );
}
