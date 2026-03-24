document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-tab-group]").forEach((group) => {
    const groupName = group.dataset.tabGroup || "default";
    const buttons = Array.from(group.querySelectorAll("[data-tab-target]"));
    const firstTarget = buttons[0]?.dataset.tabTarget;
    const storageKey = `citizen-ai-tab:${window.location.pathname}:${groupName}`;
    const url = new URL(window.location.href);
    const requestedTab = url.searchParams.get("tab");

    const activateTab = (target) => {
      if (!buttons.some((button) => button.dataset.tabTarget === target)) {
        return;
      }

      buttons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.tabTarget === target);
      });

      document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
        if (!buttons.some((button) => button.dataset.tabTarget === panel.dataset.tabPanel)) {
          return;
        }
        panel.classList.toggle("is-active", panel.dataset.tabPanel === target);
      });

      window.localStorage.setItem(storageKey, target);
      url.searchParams.set("tab", target);
      window.history.replaceState({}, "", url.toString());

      setTimeout(() => {
        document.querySelectorAll(".map-shell").forEach((node) => {
          const mapInstance = node._leaflet_map_instance;
          if (mapInstance) {
            mapInstance.invalidateSize();
          }
        });
      }, 50);
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => activateTab(button.dataset.tabTarget));
    });

    if (firstTarget) {
      const savedTab = window.localStorage.getItem(storageKey);
      const activeTarget =
        buttons.find((button) => button.dataset.tabTarget === requestedTab)?.dataset.tabTarget ||
        buttons.find((button) => button.dataset.tabTarget === savedTab)?.dataset.tabTarget ||
        buttons.find((button) => button.classList.contains("is-active"))?.dataset.tabTarget ||
        firstTarget;
      activateTab(activeTarget);
    }
  });

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
  mapNode._leaflet_map_instance = map;

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
