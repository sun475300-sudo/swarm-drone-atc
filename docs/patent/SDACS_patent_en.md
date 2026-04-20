# Patent Specification (English / PCT Draft)

**【Title of the Invention】**
SWARM DRONE AIRSPACE CONTROL AUTOMATION SYSTEM AND METHOD FUSING DYNAMIC 3D GEOFENCING AND DISTRIBUTED CONFLICT DETECTION & RESOLUTION

**【Applicant】** (to be filled)
**【Inventor】** Jang, Sunwoo
**【Filing Date】** 2026-__-__
**【International Patent Classification (IPC)】**
- G08G 5/00 (Air Traffic Control Systems)
- G05D 1/10 (Cooperative Control of Multiple Mobile Bodies)
- B64C 39/02 (Unmanned Aerial Vehicles)
- G06N 3/08 (Learning based on Artificial Intelligence)

---

## ABSTRACT

Provided is a system and method for automating airspace control of swarm drones (swarm UAVs). The system comprises: (a) a **dynamic geofencing module** that generates, in real time, a three-dimensional virtual danger fence in the form of a cylinder or sphere when an unexpected event occurs; (b) an **APF (Artificial Potential Field) path planning module** that calculates a path as a vector sum of an attractive force (target point) and a repulsive force (obstacles, other drones, fences); (c) a **distributed conflict detection and resolution (CD&R) module** in which each drone autonomously recalculates an evasion path without instructions from a central controller; and (d) a **WebGPU Compute parallel acceleration module** that guarantees a 1 Hz real-time control loop for swarms comprising hundreds to thousands of drones. The invention maintains a conflict resolution rate of 97% or higher even under high-wind conditions exceeding 10 m/s, and fundamentally eliminates the single point of failure (SPOF) inherent in centralized control.

**Representative Drawing: FIG. 1** (Conceptual diagram of the four-layer system architecture)

---

## TECHNICAL FIELD

[0001] The present invention relates to automation technology for airspace control of swarm unmanned aerial vehicles (UAVs), and more particularly, to a system and method that fuses **dynamic three-dimensional geofencing** with a **distributed conflict detection and resolution (CD&R)** technique, thereby overcoming the limitations of centralized control and enabling the safe and efficient operation of hundreds to thousands of swarm drones.

---

## BACKGROUND ART

[0002] The drone industry is rapidly expanding into logistics, defense, urban air mobility (UAM), disaster response, and smart agriculture. The number of registered drones in the Republic of Korea increased fourfold from approximately 20,000 units in 2020 to 80,000 units in 2024.

[0003] However, current airspace control technology remains in the manual control paradigm of "one drone = one pilot," which cannot accommodate the exponential growth in drone traffic.

[0004] A first problem with conventional techniques is **static geofencing**. Existing geo-zone regimes manage only pre-designated no-fly zones and cannot respond in real time to unexpected events such as manned aircraft incursion, adverse weather, or emergencies.

[0005] A second problem is the **single point of failure (SPOF)** inherent in centralized control. When a central server computes and issues paths for every drone, communication delays, network outages, or server failures jeopardize the safety of the entire swarm.

[0006] A third problem is the **real-time computation bottleneck** for large swarms. CPU-based conflict detection and path planning algorithms cannot guarantee a 1 Hz control cycle once the number of drones exceeds 100, due to O(N²) complexity.

[0007] A fourth problem is the **lack of weather adaptability**. Fixed-parameter APF approaches are vulnerable to disturbances such as strong winds and gusts, causing evasion path oscillation or failure to converge to the target.

---

## SUMMARY OF INVENTION

### Technical Problem

[0008] The present invention is directed to solving the aforementioned problems of the prior art, and addresses the following technical problems:
- Problem 1: Provide a mechanism for automatically generating a **three-dimensional virtual danger fence** reflecting in real time such unexpected factors as manned aircraft incursion, weather deterioration, and emergencies, and for immediately incorporating the fence into the paths of surrounding swarm drones.
- Problem 2: Provide a distributed control architecture in which each drone can **autonomously perform conflict detection and evasion-path recalculation** without relying on a single central controller.
- Problem 3: Provide a parallel computation acceleration technique that enables **real-time control at a 1 Hz cycle** for swarms of hundreds to thousands of drones.
- Problem 4: Provide a mechanism for automatically switching collision avoidance parameters to be **robust** against changes in weather conditions such as wind speed and gusts.

### Technical Solution

[0009] To solve the above problems, the present invention provides a swarm drone airspace control system comprising:
- (a) a **dynamic 3D geofencing module** that monitors a real-time event stream (manned aircraft position, weather, emergency zones) and, upon event occurrence, immediately creates a cylindrical or spherical virtual fence at designated coordinates and registers the fence as a repulsive source in an airspace state store;
- (b) a **distributed APF path planning module** in which each drone agent calculates a next-step velocity vector as a vector sum of an attractive force toward a goal position and a repulsive force from surrounding obstacles, other drones, and the dynamic fences, according to the following equations:

> **[Equation 1]** F_total = F_attr + Σ F_rep_i
> **[Equation 2]** F_attr = k_att · (p_goal − p_self)
> **[Equation 3]** F_rep_i = k_rep · (1/d_i − 1/d_safe)² · (p_self − p_obs_i)/|·|³,   d_i < d_safe

- (c) a **weather-adaptive parameter switching module** that automatically switches the APF parameters from a default mode to a **high-wind mode (APF_PARAMS_WINDY)** when a wind-speed sensor measurement exceeds a preset threshold (default 10 m/s), thereby increasing the repulsive gain (k_rep) and decreasing the attractive gain (k_att);
- (d) a **distributed CD&R module** that broadcasts the fence-generation event to every drone in the surrounding airspace; each drone, upon receiving the broadcast, independently performs an APF recalculation, and maintains basic avoidance behavior based on a locally cached airspace state even if communication is disrupted;
- (e) a **WebGPU Compute parallel acceleration module** that implements the APF computations, CBS (Conflict-Based Search) conflict detection, and Voronoi airspace partitioning as WebGPU Compute Shaders to parallelize them on a GPU of a browser or edge device, reducing the computational complexity for an N-drone swarm from O(N²) to effectively O(log N); and
- (f) a **four-layer system architecture** comprising a drone agent layer (10 Hz), an airspace controller layer (1 Hz), a simulation engine layer, and an operating UI/CLI layer.

### Advantageous Effects

[0010] The present invention provides the following effects:
- Preemptive collision avoidance of 97.8% (pre-avoided in 978 out of 1,000 empirical simulations)
- Average response time of less than 1.2 seconds from risk detection to evasion-path recalculation
- Elimination of the SPOF through distributed CD&R, guaranteeing swarm-wide safety even under central-server failure or communication outage
- Robustness: conflict-resolution rate of ≥ 97% maintained under 10 m/s high-wind conditions
- Scalability via WebGPU parallelization; reproducible verification framework with 38,400 Monte Carlo trials and 63 scenarios across seven metropolitan cities

---

## BRIEF DESCRIPTION OF DRAWINGS

- **FIG. 1** — Conceptual diagram of the four-layer architecture of the SDACS system
- **FIG. 2** — Flowchart of the procedure for generating a dynamic 3D geofence
- **FIG. 3** — Message sequence diagram of inter-drone broadcasts in the distributed CD&R module
- **FIG. 4** — Diagram illustrating the APF vector composition principle and high-wind mode switching conditions
- **FIG. 5** — Parallel computation pipeline based on WebGPU Compute Shaders
- **FIG. 6** — Statistical distribution graph of collision detection results (38,400 Monte Carlo trials)
- **FIG. 7** — Radar chart comparing conflict-resolution rates per scenario across the seven metropolitan cities

---

## DETAILED DESCRIPTION

### 1. Overall System Configuration (FIG. 1)

[0011] The SDACS according to the present invention comprises, as shown in FIG. 1, four layers (Layer 1 to Layer 4). The cycles and interfaces between layers are as shown in Table 1.

**[Table 1] Per-Layer Cycles and Interfaces**

| Layer | Component | Cycle | Upper-Layer Interface |
|-------|-----------|-------|------------------------|
| Layer 1 | `_DroneAgent` (SimPy) | 10 Hz | Drone status reporting |
| Layer 2 | `AirspaceController` | 1 Hz | Path modification commands |
| Layer 3 | `SwarmSimulator` | event-based | Environment state |
| Layer 4 | Dash UI, CLI | on-demand | User commands |

### 2. Dynamic 3D Geofencing Embodiment (FIG. 2)

[0012] The dynamic geofencing module operates through the following steps:
- **Step S210**: An event-monitoring thread receives unexpected events from external APIs (meteorological service, air traffic control, emergency system) and from the drones' own sensors (ADS-B-like signals).
- **Step S220**: The shape (cylinder/sphere) and size of the fence are determined according to the event type. For example, a cylinder of radius 500 m and altitude ±150 m is generated upon manned-helicopter incursion.
- **Step S230**: The generated fence is recorded in the airspace state store with a Time-To-Live (TTL).
- **Step S240**: The stored fence is injected into the repulsive-source list during APF computation.
- **Step S250**: The fence is automatically removed upon TTL expiration.

### 3. Distributed CD&R Embodiment (FIG. 3)

[0013] In the distributed CD&R of the present invention, each drone maintains a local airspace cache and independently executes the following algorithm upon receiving a dynamic-fence creation event:

```
# Algorithm 1: Distributed CD&R pseudocode
def on_fence_broadcast(self, fence):
    self.local_airspace.add(fence)
    if fence.affects_path(self.planned_path):
        new_path = apf.recompute(
            self_state=self.state,
            goal=self.goal,
            obstacles=self.local_airspace.all(),
            wind=self.wind_sensor.read(),
        )
        self.planned_path = new_path
```

### 4. APF Path Planning and High-Wind Mode (FIG. 4)

[0014] The APF parameter sets are defined as follows and are automatically switched when the wind-speed threshold is exceeded:

**[Table 2] APF Parameter Sets**

| Parameter | Default Mode (≤ 10 m/s) | High-Wind Mode (> 10 m/s) |
|-----------|--------------------------|----------------------------|
| k_att (attractive gain) | 1.0 | 0.6 |
| k_rep (repulsive gain) | 2.0 | 3.5 |
| d_safe (safe distance, m) | 30 | 50 |
| v_max (max velocity, m/s) | 15 | 10 |

### 5. WebGPU Compute Parallel Acceleration (FIG. 5)

[0015] The WebGPU Compute Shader bulk-uploads the position vectors of N drones to a GPU buffer, and each workgroup independently computes APF force vectors. The memory access pattern is arranged to guarantee coalesced access; the results are returned to the CPU and converted into control commands.

### 6. Verification Methodology

[0016] Performance verification of the present invention was conducted in three stages:
- **Stage V1**: 1,000 iterations of a single scenario — conflict-resolution rate 97.8%
- **Stage V2**: 38,400 Monte Carlo sweeps — exhaustive parameter-space exploration
- **Stage V3**: 63 empirical scenarios (seven metropolitan cities × nine scenarios) — all passed

---

## CLAIMS

### **Claim 1** *(Independent claim — System)*

A system for automating airspace control of swarm drones, comprising:

a **dynamic geofencing module** configured to monitor real-time events, to generate a virtual danger fence of a three-dimensional cylindrical or spherical shape at airspace coordinates, and to register the fence as a repulsive source;

an **APF path planning module** configured to calculate, per drone, a next-step velocity vector as a vector sum of an attractive force toward a goal position and repulsive forces from surrounding obstacles, other drones, and the fence;

a **distributed conflict detection and resolution (CD&R) module** configured to broadcast a creation event of the fence to every drone in the surrounding airspace, and to cause each drone to autonomously recalculate a path without instruction from a central controller; and

a **parallel acceleration module** configured to execute the APF path planning computations and conflict detection computations in parallel via GPU Compute Shaders.

### **Claim 2** *(Dependent — weather adaptation)*

The system of Claim 1, further comprising a **weather-adaptive parameter switching module** configured to, when a wind-speed sensor measurement exceeds a preset threshold, increase a repulsive gain and decrease an attractive gain of the APF path planning module.

### **Claim 3** *(Dependent — four-layer structure)*

The system of Claim 1, wherein the system comprises four layers consisting of:
a drone agent layer configured to update drone states at 10 Hz;
an airspace controller layer configured to integrally execute the dynamic geofencing, APF, and CD&R at 1 Hz;
a simulation layer providing scenario-based, weather-based, and Monte Carlo verification; and
an operating interface layer providing user commands and 3D visualization.

### **Claim 4** *(Dependent — distributed autonomy)*

The system of Claim 1, wherein the distributed CD&R module is configured to maintain avoidance behavior based on a locally cached airspace state at each drone even under communication disruption.

### **Claim 5** *(Dependent — fence TTL)*

The system of Claim 1, wherein the dynamic geofencing module is configured to assign a Time-To-Live (TTL) to a generated virtual danger fence and to automatically remove the fence from an airspace state store upon TTL expiration.

### **Claim 6** *(Independent — Method)*

A method of automating airspace control of swarm drones, performed by a computing device, comprising:
(a) receiving unexpected situations from an external event stream;
(b) generating a three-dimensional virtual danger fence based on the received event and registering the fence in an airspace state store;
(c) broadcasting the generated fence to swarm drones within a surrounding airspace;
(d) recalculating, at each drone, an evasion path via GPU parallel computation by vector-summing an attractive force toward a goal position and repulsive forces from obstacles, other drones, and the fence; and
(e) generating and transmitting drone control commands according to the recalculated evasion path.

### **Claim 7** *(Dependent — high-wind mode)*

The method of Claim 6, wherein step (d) comprises, when a wind-speed measurement exceeds 10 m/s, increasing a gain of the repulsive force by at least 1.5 times a gain of a default mode.

### **Claim 8** *(Dependent — medium)*

A computer-readable recording medium storing a program for executing on a computer the method of any one of Claims 6 to 7.

---

## APPENDIX — Terminology

- **APF (Artificial Potential Field)**: a real-time path-planning technique that synthesizes a drone's movement vector by treating the goal as an attractor and obstacles as repellors.
- **CD&R (Conflict Detection & Resolution)**: a technique for detecting potential collisions among drones and computing evasion paths.
- **SPOF (Single Point Of Failure)**: a point where a single failure causes a system-wide outage.
- **WebGPU Compute**: a next-generation Web API for GPU parallel computation in browsers and edge devices.

---

**【Date】** 2026-04-20
**【References】** `docs/patent/SDACS_특허명세서.md`, `docs/proposal/아이디어_상세설명.txt`, `docs/architecture.md`
