import heapq
import random
import networkx as nx
import folium
import streamlit as st
from streamlit_folium import st_folium

# ==========================================
# 1. GRAPH & DATA CONFIGURATION (WEEK 8)
# ==========================================
NODES = {
    "Base Alpha": (17.3850, 78.4866),
    "Base Beta": (17.3880, 78.5000),      
    "Junction North": (17.3890, 78.4880),
    "Junction South": (17.3830, 78.4910),
    "Junction East": (17.3870, 78.4950),
    "Highway 1": (17.3920, 78.4900),
    "Accident Zone": (17.3910, 78.4980),
    "City Hospital": (17.3820, 78.5020),
    "District Hospital": (17.3950, 78.4850) 
}

BASE_EDGES = [
    ("Base Alpha", "Junction North", 3),
    ("Base Alpha", "Junction South", 2),
    ("Base Beta", "Junction East", 4),       
    ("Base Beta", "City Hospital", 3),       
    ("Junction North", "Highway 1", 4),
    ("Junction North", "Junction East", 5),
    ("Junction North", "District Hospital", 6), 
    ("Junction South", "Junction East", 3),
    ("Junction South", "City Hospital", 8),
    ("Highway 1", "Accident Zone", 6),
    ("Highway 1", "District Hospital", 5),
    ("Junction East", "Accident Zone", 4),
    ("Accident Zone", "City Hospital", 5),
    ("Accident Zone", "District Hospital", 4) # Added to make multi-hospital viable
]

# ==========================================
# 2. CORE ALGORITHMS
# ==========================================
# W8 Improvement 1 & 2: Dijkstra using Min-Heap and Adjacency List
def run_dijkstra_all(graph, start):
    distances = {node: float("inf") for node in graph}
    paths = {node: [] for node in graph}
    distances[start] = 0
    paths[start] = [start]
    
    pq = [(0, start)]
    while pq:
        curr_dist, curr_node = heapq.heappop(pq)
        if curr_dist > distances[curr_node]: continue
        for neighbor, weight in graph.get(curr_node, []):
            new_dist = curr_dist + weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                paths[neighbor] = paths[curr_node] + [neighbor]
                heapq.heappush(pq, (new_dist, neighbor))
    return distances, paths

def run_bfs(graph, start, target):
    visited = set([start])
    queue = [(start, [start])]
    while queue:
        curr, path = queue.pop(0)
        if curr == target: return path
        for neighbor, _ in graph.get(curr, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return []

def run_dfs(graph, start, target):
    visited = set()
    stack = [(start, [start])]
    while stack:
        curr, path = stack.pop()
        if curr not in visited:
            visited.add(curr)
            if curr == target: return path
            for neighbor, _ in sorted(graph.get(curr, []), reverse=True):
                if neighbor not in visited:
                    stack.append((neighbor, path + [neighbor]))
    return []

def calculate_path_time(path, live_edges):
    if not path: return float("inf")
    total_time = 0
    for i in range(len(path)-1):
        u, v = path[i], path[i+1]
        weight = live_edges.get(f"{u}-{v}", live_edges.get(f"{v}-{u}", None))
        if weight is None: return float("inf") 
        total_time += weight
    return total_time

# ==========================================
# 3. STREAMLIT UI & STATE MANAGEMENT
# ==========================================
st.set_page_config(page_title="EMS Router Pro", page_icon="🚑", layout="wide")
st.title("🚑 Intelligent EMS Routing Dashboard (Full System)")

if "traffic_data" not in st.session_state:
    st.session_state.traffic_data = {f"{u}-{v}": w for u, v, w in BASE_EDGES}

st.sidebar.header("📡 Scenario Command Center")
priority = st.sidebar.radio("🚨 Emergency Priority:", ["High (Cardiac/Trauma)", "Medium (Fracture)", "Low (Minor)"])

if st.sidebar.button("🚦 Simulate Live Traffic Spike"):
    st.session_state.traffic_data = {
        f"{u}-{v}": w + random.choice([0, 0, 5, 12, 25]) 
        for u, v, w in BASE_EDGES
    }

st.sidebar.subheader("🚧 Physical Constraints")
blocked_road = st.sidebar.selectbox("Simulate Total Road Closure:", ["None"] + [f"{u} ➔ {v}" for u, v, _ in BASE_EDGES])

st.sidebar.subheader("🔬 Algorithm Overlays")
show_bfs = st.sidebar.checkbox("Show BFS Route (Yellow Dashed)")
show_dfs = st.sidebar.checkbox("Show DFS Route (Cyan Dashed)")

# Build Graphs (Adjacency List structure for W8)
live_graph = {node: [] for node in NODES}
nx_graph = nx.Graph()

for u, v, base_w in BASE_EDGES:
    nx_graph.add_edge(u, v) # Added to full graph to generate human options
    if f"{u} ➔ {v}" == blocked_road or f"{v} ➔ {u}" == blocked_road:
        continue 
    live_w = st.session_state.traffic_data[f"{u}-{v}"]
    live_graph[u].append((v, live_w))
    live_graph[v].append((u, live_w))

# ==========================================
# 4. W8 MULTI-DISPATCH OPTIMIZATION LOGIC
# ==========================================
# Run Dijkstra OUTWARDS from the Accident Zone to find the closest Base & Hospital
dist_from_acc, paths_from_acc = run_dijkstra_all(live_graph, "Accident Zone")

bases = {"Base Alpha": dist_from_acc.get("Base Alpha", float('inf')), 
         "Base Beta": dist_from_acc.get("Base Beta", float('inf'))}
best_base = min(bases, key=bases.get)

hospitals = {"City Hospital": dist_from_acc.get("City Hospital", float('inf')), 
             "District Hospital": dist_from_acc.get("District Hospital", float('inf'))}
best_hospital = min(hospitals, key=hospitals.get)

if bases[best_base] == float('inf') or hospitals[best_hospital] == float('inf'):
    st.error("🚨 CRITICAL FAILURE: Target location is completely isolated. Initiate aerial dispatch.")
    st.stop()

# Reconstruct the two-part optimal path
path_to_patient = paths_from_acc[best_base][::-1] 
path_to_hosp = paths_from_acc[best_hospital]      
full_opt_route = path_to_patient[:-1] + path_to_hosp
opt_total_time = bases[best_base] + hospitals[best_hospital]

# Calculate BFS / DFS for comparison
bfs_route = run_bfs(live_graph, best_base, "Accident Zone") + run_bfs(live_graph, "Accident Zone", best_hospital)[1:]
dfs_route = run_dfs(live_graph, best_base, "Accident Zone") + run_dfs(live_graph, "Accident Zone", best_hospital)[1:]
bfs_time = calculate_path_time(bfs_route, st.session_state.traffic_data)
dfs_time = calculate_path_time(dfs_route, st.session_state.traffic_data)

# Generate & Rank Human Routes (from selected best base to selected best hospital)
all_paths_to_patient = list(nx.all_simple_paths(nx_graph, best_base, "Accident Zone"))
all_paths_to_hosp = list(nx.all_simple_paths(nx_graph, "Accident Zone", best_hospital))
all_valid_routes = [p1 + p2[1:] for p1 in all_paths_to_patient for p2 in all_paths_to_hosp]

ranked_routes = []
for route in all_valid_routes:
    t = calculate_path_time(route, st.session_state.traffic_data)
    ranked_routes.append({"route": route, "time": t})

ranked_routes.sort(key=lambda x: x["time"])

route_options = []
for data in ranked_routes:
    r_str = " ➔ ".join(data["route"])
    if data["time"] == float('inf'):
        display = f"❌ ROAD CLOSED: {r_str}"
    elif data["time"] == opt_total_time:
        display = f"✅ AI OPTIMAL ({data['time']} mins): {r_str}"
    else:
        display = f"⚠️ +{data['time'] - opt_total_time} mins slower ({data['time']} mins): {r_str}"
    route_options.append((data, display))

# ==========================================
# 5. DASHBOARD METRICS & VALIDATOR
# ==========================================
st.subheader("Global Mission Telemetry")
if "High" in priority:
    st.error(f"**PRIORITY OVERRIDE:** {priority}. System routing for absolute minimum latency.")

c1, c2, c3 = st.columns(3)
c1.metric(f"Dispatch: {best_base} ➔ Patient", f"{bases[best_base]} Mins")
c2.metric(f"Patient ➔ ER: {best_hospital}", f"{hospitals[best_hospital]} Mins")
c3.metric("AI Total Mission Latency", f"{opt_total_time} Mins", delta="Global Optimized")

st.markdown("---")
col_human, col_algo = st.columns(2)

with col_human:
    st.subheader("🧑‍✈️ Smart Custom Route Validator")
    selected_tuple = st.selectbox(
        "Select a path from the ranked list below:", 
        options=route_options,
        format_func=lambda x: x[1] 
    )
    
    selected_custom_route = selected_tuple[0]["route"]
    custom_route_time = selected_tuple[0]["time"]
    
    if custom_route_time == float('inf'):
        st.error("🛑 **INVALID ROUTE:** You selected a route that attempts to use a completely closed road.")
    elif custom_route_time > opt_total_time:
        st.warning(f"**Sub-Optimal Decision:** Human route takes **{custom_route_time} mins**. AI avoids traffic and is **{custom_route_time - opt_total_time} mins faster!**")
    else:
        st.success(f"**Perfect Match:** Route exactly matches the AI's logic! ({opt_total_time} mins)")

with col_algo:
    st.subheader("⚙️ Algorithm Efficiency Comparison")
    st.info(f"🟢 **Dijkstra (Min-Heap):** {opt_total_time} mins (Traffic Aware)")
    st.warning(f"🟡 **BFS Engine:** {bfs_time} mins (Blind to Traffic)")
    st.info(f"🔵 **DFS Engine:** {dfs_time} mins (Erratic Pathing)")

# ==========================================
# 6. ADVANCED GEOSPATIAL VISUALIZATION
# ==========================================
m = folium.Map(location=[17.3870, 78.4930], zoom_start=15, tiles="CartoDB dark_matter")

# Draw all live edges
for u, v, base_w in BASE_EDGES:
    if f"{u} ➔ {v}" == blocked_road or f"{v} ➔ {u}" == blocked_road:
        continue 
    live_w = st.session_state.traffic_data[f"{u}-{v}"]
    if live_w > base_w + 10:
        color, weight, opac = "#ff4b4b", 5, 0.8
    elif live_w > base_w:
        color, weight, opac = "#ffa500", 4, 0.7
    else:
        color, weight, opac = "#4b4bff", 3, 0.5
    folium.PolyLine([NODES[u], NODES[v]], color=color, weight=weight, opacity=opac, tooltip=f"{u} ↔ {v}: {live_w} mins").add_to(m)

# Draw BFS / DFS Overlays
if show_bfs and bfs_route:
    folium.PolyLine([NODES[node] for node in bfs_route], color="yellow", weight=5, opacity=0.9, dash_array="10").add_to(m)

if show_dfs and dfs_route:
    folium.PolyLine([NODES[node] for node in dfs_route], color="cyan", weight=5, opacity=0.9, dash_array="10").add_to(m)

# Draw the Optimal OR Custom Route
if selected_custom_route == full_opt_route:
    folium.PolyLine([NODES[node] for node in full_opt_route], color="#00ff00", weight=8, opacity=0.8, tooltip=f"AI Route: {opt_total_time} mins").add_to(m)
else:
    folium.PolyLine([NODES[node] for node in selected_custom_route], color="#b026ff", weight=8, opacity=0.9, dash_array="10", tooltip=f"Custom: {custom_route_time} mins").add_to(m)

# Draw Markers
for node, coords in NODES.items():
    if "Base" in node: icon = folium.Icon(color="darkblue", icon="ambulance", prefix="fa")
    elif node == "Accident Zone": icon = folium.Icon(color="red", icon="warning", prefix="fa")
    elif "Hospital" in node: icon = folium.Icon(color="green", icon="h-square", prefix="fa")
    else: icon = folium.Icon(color="gray", icon="traffic-light", prefix="fa")
    folium.Marker(location=coords, tooltip=node, icon=icon).add_to(m)

st_folium(m, width=1200, height=550)