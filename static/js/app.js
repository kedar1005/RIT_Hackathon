document.addEventListener("DOMContentLoaded", () => {
  const mapNode = document.getElementById("city-map");
  if (!mapNode || typeof L === "undefined") return;

  let points = [];
  try {
    points = JSON.parse(mapNode.dataset.mapPoints || "[]");
  } catch (error) {
    points = [];
  }

  const defaultCenter = [16.705, 74.2433];
  const center = points.length ? [points[0].lat, points[0].lon] : defaultCenter;
  const map = L.map(mapNode).setView(center, points.length ? 11 : 10);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  const bounds = [];
  points.forEach((point) => {
    if (typeof point.lat !== "number" || typeof point.lon !== "number") return;

    const color =
      point.urgency === "High" ? "#dc2626" :
      point.urgency === "Medium" ? "#d97706" :
      "#15803d";

    const marker = L.circleMarker([point.lat, point.lon], {
      radius: 8,
      color,
      fillColor: color,
      fillOpacity: 0.8,
      weight: 2
    }).addTo(map);

    marker.bindPopup(
      `<strong>#CMP-${String(point.id).padStart(4, "0")}</strong><br>` +
      `${point.category || "Unknown"}<br>` +
      `${point.status || "Pending"} • ${point.urgency || "Medium"}<br>` +
      `${point.address || "No address"}`
    );
    bounds.push([point.lat, point.lon]);
  });

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [24, 24] });
  }
});
